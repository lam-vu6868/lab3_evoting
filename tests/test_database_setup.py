"""
FILE: tests/test_database_setup.py
MỤC ĐÍCH: Kiểm tra chặng 1 trên PostgreSQL đang chạy bằng Docker Compose.
CÁCH CHẠY: python -m unittest tests.test_database_setup -v, từ thư mục gốc.
KIỂM TRA: 5 bảng, 3 role, đăng nhập bằng mật khẩu env và quyền từng role.
Không in secret hoặc đọc nội dung phiếu. Probe quote password tạo role tạm
trong transaction rồi ROLLBACK; không đổi mật khẩu role đang dùng.
PHỤ THUỘC: Docker đang chạy, service postgres healthy; Python stdlib.
"""
from pathlib import Path
import json
import subprocess
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


def psql(sql, role=None):
    command = ['docker', 'compose', 'exec', '-T', 'postgres']
    args = ['psql', '-X', '-w', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
            '-v', 'VERBOSITY=sqlstate', '-d', 'evoting']
    if role:
        password_env = {'app_user': 'APP_USER_PASSWORD',
                        'admin_app': 'ADMIN_USER_PASSWORD',
                        'tally_user': 'TALLY_USER_PASSWORD'}[role]
        # Shell sees only a fixed env-variable name, never an interpolated secret.
        command += ['sh', '-c', f'export PGPASSWORD="${password_env}"; exec "$@"',
                    'db-check', *args, '-h', '127.0.0.1', '-U', role]
    else:
        command += [*args, '-U', 'postgres']
    return subprocess.run(command, cwd=ROOT, input=sql, capture_output=True,
                          text=True, encoding='utf-8', timeout=30)


class DatabaseSetupTests(unittest.TestCase):
    def test_tables_and_candidates(self):
        result = psql("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
        self.assertEqual(result.returncode, 0, 'Cannot inspect PostgreSQL tables')
        self.assertEqual(result.stdout.split(),
                         ['candidates', 'used_nonces', 'voter_status', 'voters', 'votes'])
        result = psql('SELECT count(*) FROM candidates;')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), '3')

    def test_roles_are_not_privileged(self):
        result = psql("SELECT count(*) FROM pg_roles WHERE rolname IN "
                      "('app_user','admin_app','tally_user') AND rolcanlogin "
                      "AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole;")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), '3')

    def test_each_role_can_login_and_read_candidates(self):
        for role in ['app_user', 'admin_app', 'tally_user']:
            with self.subTest(role=role):
                result = psql('SELECT current_user; SELECT count(*) FROM candidates;', role)
                self.assertEqual(result.returncode, 0, f'{role}: login/read failed (secret hidden)')
                self.assertEqual(result.stdout.split(), [role, '3'])

    def test_vote_permissions(self):
        for role in ['app_user', 'admin_app']:
            with self.subTest(role=role):
                result = psql('SELECT 1 FROM votes LIMIT 0;', role)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('42501', result.stderr, 'Expected insufficient_privilege')
        result = psql('SELECT 1 FROM votes LIMIT 0;', 'tally_user')
        self.assertEqual(result.returncode, 0)
        result = psql("SELECT json_build_array(r, has_table_privilege(r,'votes','INSERT'), "
                      "has_table_privilege(r,'votes','UPDATE'), has_table_privilege(r,'votes','DELETE')) "
                      "FROM unnest(ARRAY['app_user','admin_app','tally_user']) r;")
        self.assertEqual(result.returncode, 0)
        self.assertEqual([json.loads(line) for line in result.stdout.splitlines() if line],
                         [['app_user', True, False, False], ['admin_app', False, False, False],
                          ['tally_user', False, False, False]])

    def test_password_sql_quoting(self):
        role = 'setup_probe_' + uuid.uuid4().hex
        # Synthetic test password, not a real credential. Both apostrophe and backslash.
        sql = f"""BEGIN;
\\set probe_password 'quote''and\\\\backslash'
SELECT format('CREATE ROLE %I NOLOGIN PASSWORD %L', '{role}', :'probe_password')
\\gexec
ROLLBACK;
SELECT count(*) FROM pg_roles WHERE rolname = '{role}';
"""
        result = psql(sql)
        self.assertEqual(result.returncode, 0, 'Quoted password role creation failed')
        self.assertEqual(result.stdout.splitlines()[-1], '0')


if __name__ == '__main__':
    unittest.main()

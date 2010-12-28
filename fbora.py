##############################################################################
# Copyright (c) 2007, Hajime Nakagami<nakagami@da2.so-net.ne.jp>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
##############################################################################
import sys, clr
clr.AddReference("System.Data")
import System.IO
from System.Convert import IsDBNull
from System.Data import *

import fbutil
import orautil

last_execute_sql = ''

def copy_to_fb(host, login, password, conn_d, to_upper = True,
    set_default = False, foreign_keys = False, check_constraints = False, 
    need_data_copy=False, debug=False):
    global last_execute_sql

    ora_db = orautil.OraDatabase(host, login, password)
    ora_db.open()

    fb_db = fbutil.FbDatabase(conn_d,
                    create_flag=True,forced_writes=True,over_write=True)
    fb_db.open()

    for t in ora_db.tables():
        sqlStmt = ora_db.create_fbsql(t['TABLE_NAME'], to_upper, set_default)
        if debug:
            print sqlStmt
        last_execute_sql = sqlStmt
        fb_db.execute_noq(sqlStmt)

    if need_data_copy:
        for t in ora_db.tables():
            tab_name = t['TABLE_NAME']
            columns = [c['COLUMN_NAME'] for c in ora_db.columns(tab_name)]
            insert_sql = 'insert into "'
            if to_upper:
                insert_sql += tab_name.upper()
            else:
                insert_sql += tab_name
            insert_sql += '" ("'
            if to_upper:
                insert_sql += '","'.join([c.upper() for c in columns])
            else:
                insert_sql += '","'.join(columns)
            insert_sql += '''") values ('''
            insert_sql += ','.join(['@'+c for c in columns])
            insert_sql += ''')'''
            sqlStmt = 'select * from "' + tab_name + '"'
            if debug:
                print sqlStmt
                print insert_sql
            last_execute_sql = sqlStmt
            dr = ora_db.execute(sqlStmt)
            for r in dr:
                params = {}
                for cname in columns:
                    v = r[cname]
                    if type(v) == System.Int16 or type(v) == System.Byte:
                        v = int(v)
                    params['@' + cname] = v
                last_execute_sql = insert_sql + '\n' + str(params)
                fb_db.execute_noq(insert_sql, params)
            dr.Close()

    if foreign_keys:
        for t in ora_db.tables():
            fks = ora_db.foreign_keys(t['TABLE_NAME'], to_upper)
            for k in fks:
                fk = fks[k]
                sqlStmt = 'alter table "'
                if to_upper:
                    sqlStmt += t['TABLE_NAME'].upper()
                else:
                    sqlStmt += t['TABLE_NAME']
                sqlStmt += '" add foreign key("'
                sqlStmt += '","'.join(fk['COLUMN_NAME'])
                sqlStmt += '") references "%s"("' % (fk['REF_TABLE'], )
                sqlStmt += '","'.join(fk['REF_COLUMN'])
                sqlStmt += '")'
                if debug:
                    print sqlStmt
                fb_db.execute_noq(sqlStmt)

    if check_constraints:
        for t in ora_db.tables():
            chks = ora_db.check_constraints(t['TABLE_NAME'])
            for k in chks:
                tab_name = t['TABLE_NAME']
                if to_upper:
                    tab_name = tab_name.upper()
                sqlStmt = 'alter table "%s" add constraint "%s" check (%s)' % \
                    (tab_name, k, chks[k])
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                fb_db.execute_noq(sqlStmt)

    ora_db.close()
    return fb_db

def fb_fieldtype_to_string(d, fb_db):
    if d['FIELD_NAME'][:4] != 'RDB$':   # Domain
        t = fb_db.domains(d['FIELD_NAME'].strip())
    else:
        t = d

    type_name = t['TYPE_NAME'].strip()
    if type_name == 'SHORT':
        s = 'INT'
    elif type_name == 'LONG':
        s = 'INT'
    elif type_name == 'TEXT':
        s = 'CHAR(' + str(t['CHARACTER_LENGTH']) + ')'
    elif type_name == 'VARYING':
        s = 'VARCHAR2(' + str(t['CHARACTER_LENGTH']) + ')'
    elif type_name == 'INT64':
        if t['FIELD_SUB_TYPE'] == 1:
            s = 'NUMBER'
        else:
            s = 'NUMBER'
        s += '('+str(t['FIELD_PRECISION'])+','+str(t['FIELD_SCALE']*-1)+')'
    elif type_name == 'BLOB' and t['FIELD_SUB_TYPE'] == 0:
        s = 'BLOB'
    elif type_name == 'BLOB' and t['FIELD_SUB_TYPE'] == 1:
        s = 'CLOB'
    elif type_name == 'DOUBLE':
        s = 'FLOAT'
    elif type_name == 'TIMESTAMP' or type_name == 'DATE':
        s = 'TIMESTAMP'
    else:
        s = type_name

    if not IsDBNull(t['DEFAULT_SOURCE']):
        s += ' ' + t['DEFAULT_SOURCE']

    if d['NULL_FLAG'] == 1:
        s += ' NOT NULL'

    return s

def copy_from_fb(host, login, password, conn_d, to_upper,
    set_default = False, foreign_keys = False, check_constraints = False, 
    need_data_copy=False, debug=False):
    global last_execute_sql

    ora_db = orautil.OraDatabase(host, login, password)
    ora_db.open()

    fb_db = fbutil.FbDatabase(conn_d)
    fb_db.open()

    for t in ora_db.tables():
        fks = ora_db.foreign_keys(t['TABLE_NAME'], False)
        for k in fks:
            sqlStmt = 'alter table "%s" drop constraint "%s"' % (
                                                t['TABLE_NAME'], k)
            if debug:
                print sqlStmt
            ora_db.execute_noq(sqlStmt)
        
    for t in ora_db.tables():
        sqlStmt = 'drop table "' + t['TABLE_NAME'] + '"'
        if debug:
            print sqlStmt
        last_execute_sql = sqlStmt
        ora_db.execute_noq(sqlStmt)

    for t in fb_db.tables():
        tab_name = t['NAME'].strip()
        pks = fb_db.primary_keys(tab_name)
        uks = fb_db.unique_keys(tab_name)
        if to_upper:
            sqlStmt = 'create table "' + tab_name.upper() + '" (\n'
        else:
            sqlStmt = 'create table "' + tab_name + '" (\n'
        col_str = []
        for c in fb_db.columns(tab_name):
            s = '    "' + c['NAME'].strip() + '" '
            if to_upper:
                s = s.upper()
            s += fb_fieldtype_to_string(c, fb_db)
            if c['NAME'].strip() in uks:
                s += ' UNIQUE'
            col_str.append(s) 
        sqlStmt += ",\n".join(col_str)
        if len(pks):
            if to_upper:
                pks = [k.upper() for k in pks]
            sqlStmt += ',\n    PRIMARY KEY ("' + '","'.join(pks) + '")'
        sqlStmt += ")"
        last_execute_sql = sqlStmt
        if debug:
            print sqlStmt
        ora_db.execute_noq(sqlStmt)

    if need_data_copy:
        for t in fb_db.tables():
            tab_name = t['NAME'].strip()
            insert_sql = '''insert into "%s" ("''' % (tab_name, )
            columns = [c['NAME'].strip() for c in fb_db.columns(tab_name)]
            insert_sql += '","'.join(columns)
            insert_sql += '''") values ('''
            insert_sql += ','.join([':'+c for c in columns])
            insert_sql += ''')'''

            sqlStmt = 'select * from "' + tab_name + '"'

            if debug:
                print sqlStmt
                print insert_sql

            last_execute_sql = sqlStmt
            dr = fb_db.execute(sqlStmt)
            for r in dr:
                params = {}
                for c in columns:
                    v = r[c]
                    if type(v) == System.Int16:
                        v = int(v)
                    params[c] = v
                last_execute_sql = insert_sql + '\n' + str(params)
                ora_db.execute_noq(insert_sql, params)
            dr.Close()

    if foreign_keys:
        for t in ora_db.tables():
            fks = ora_db.foreign_keys(t['TABLE_NAME'], False)
            for k in fks:
                fk = fks[k]
                sqlStmt = 'alter table "'
                if to_upper:
                    sqlStmt += t['TABLE_NAME'].upper()
                    sqlStmt += '" add foreign key("'
                    sqlStmt += '","'.join([s.upper() for s in fk['COLUMN_NAME']])
                    sqlStmt += '") references "%s"("' % (fk['REF_TABLE'].upper(), )
                    sqlStmt += '","'.join([s.upper() for s in fk['REF_COLUMN']])
                else:
                    sqlStmt += t['TABLE_NAME']
                    sqlStmt += '" add foreign key("'
                    sqlStmt += '","'.join(fk['COLUMN_NAME'])
                    sqlStmt += '") references "%s"("' % (fk['REF_TABLE'], )
                    sqlStmt += '","'.join(fk['REF_COLUMN'])
                sqlStmt += '")'
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                ora_db.execute_noq(sqlStmt)

    if check_constraints:
        for t in fb_db.tables():
            tab_name = t['NAME'].strip()
            for chk in fb_db.check_constraints(tab_name):
                sqlStmt = 'alter table "%s" add constraint "%s" %s' % \
                            (tab_name, chk['CHECK_NAME'], chk['CHECK_SOURCE'])
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                ora_db.execute_noq(sqlStmt)

    ora_db.close()
    fb_db.close()

if __name__ == '__main__':
    if len(sys.argv) == 2:
        testdir = sys.argv[1]
        if testdir[-1] != '\\':
            testdir = testdir + '\\'
    else:
        testdir = System.IO.Path.GetTempPath()
        
    print 'testdir=' + testdir

    conn_d = {
        'User' : 'SYSDBA',
        'Password' : 'masterkey',
        'DataSource' : 'localhost',
        'Database' : testdir + 'test_ora.fdb',
        'Charset' : 'UNICODE_FSS', 
    }

    fb_db = copy_to_fb('localhost', 'scott', 'tiger', conn_d, to_upper=False,
        set_default=True, foreign_keys=True, check_constraints=True,
        need_data_copy=True, debug=True)
    fb_db.close()
    copy_from_fb('localhost', 'tiger', 'scott', conn_d, to_upper=False,
        set_default=True, foreign_keys=True, check_constraints=True, 
        need_data_copy=True, debug=True)
    

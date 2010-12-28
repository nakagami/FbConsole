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
import sqlutil

last_execute_sql = ''

def copy_to_fb(host, login, password, db_name, conn_d, to_upper = True,
    set_default = False, foreign_keys = False, check_constraints = False, 
    need_data_copy=False, debug=False):
    global last_execute_sql

    smo = sqlutil.SqlSmo(host, login, password)
    sql_schema = smo.database(db_name)
    sql_db = sqlutil.SqlDatabase(host, login, password, db_name)
    sql_db.open()

    fb_db = fbutil.FbDatabase(conn_d,
                    create_flag=True,forced_writes=True,over_write=True)
    fb_db.open()

    for u in sql_schema.domains():
        sqlStmt = u.create_fbsql()
        if debug:
            print sqlStmt
        last_execute_sql = sqlStmt
        fb_db.execute_noq(sqlStmt)
    for t in sql_schema.tables():
        sqlStmt = t.create_fbsql(to_upper, set_default)
        if debug:
            print sqlStmt
        last_execute_sql = sqlStmt
        fb_db.execute_noq(sqlStmt)

    if need_data_copy:
        for t in sql_schema.tables():
            insert_sql = t.insert_fbsql(to_upper)
            sqlStmt = 'select * from "' + str(t) + '"'
            if debug:
                print sqlStmt
                print insert_sql
            last_execute_sql = sqlStmt
            dr = sql_db.execute(sqlStmt)
            for r in dr:
                params = {}
                for cname in t.columns_name():
                    v = r[cname]
                    if type(v) == System.Int16 or type(v) == System.Byte:
                        v = int(v)
                    params['@' + cname] = v
                last_execute_sql = insert_sql + '\n' + str(params)
                fb_db.execute_noq(insert_sql, params)
            dr.Close()
    for t in sql_schema.tables():
        for c in t.columns():
            id = c.identity()
            if id:
                tab_name = str(t)
                col_name = str(c)
                if to_upper:
                    tab_name = tab_name.upper()
                    col_name = col_name.upper()
                inc = id[1]
                sqlStmt = "select ident_current('" + tab_name + "')"
                last_execute_sql = sqlStmt
                seed = sql_db.execute_sca(sqlStmt)
                if not IsDBNull(seed):
                    seed += inc 
                else:
                    seed = id[0]
                sqlStmt = fbutil.create_generator_and_trigger_sql(
                                            tab_name, col_name, seed, inc)
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                fbutil.FbDatabase(conn_d).execute_batch(sqlStmt)

    if foreign_keys:
        for t in sql_schema.tables():
            tab_name = str(t)
            if to_upper:
                tab_name = tab_name.upper()
            for fk in t.foreign_keys(to_upper):
                sqlStmt = 'alter table "' + tab_name + '" add foreign key("'
                sqlStmt += '","'.join(fk[1])
                sqlStmt += '") references "%s"("' % (fk[2], )
                sqlStmt += '","'.join(fk[3])
                sqlStmt += '")'
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                fb_db.execute_noq(sqlStmt)

    if check_constraints:
        for t in sql_schema.tables():
            for (name, expr) in t.checks(to_upper):
                tab_name = str(t)
                if to_upper:
                    tab_name = tab_name.upper()
                sqlStmt = 'alter table "%s" add constraint %s check (%s)' % \
                    (tab_name, name, expr)
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                fb_db.execute_noq(sqlStmt)

    sql_db.close()
    return fb_db

def fbexpr_to_sqlexpr(expr):
    d = {
        'CURRENT_DATE':'GETDATE()'
    }
    s = ''
    i = 0
    while i < len(expr):
        if expr[i] == "'":
            s += expr[i]
            i += 1
            while expr[i] != "'":
                s += expr[i]
                i += 1
            s += expr[i]
            i += 1
        elif expr[i] == '"':
            s += '['
            i += 1
            while expr[i] != '"':
                s += expr[i]
                i += 1
            s += ']'
            i += 1
        else:
            found = False
            for k in d:
                if expr[i:i+len(k)].upper()==k:
                    s += d[k]
                    i += len(k)
                    found = True
            if not found:
                s += expr[i]
                i += 1
    return s

def fb_domain_to_string(d):
    type_name = d['TYPE_NAME'].strip()
    if type_name == 'SHORT':
        s = 'SMALLINT'
    elif type_name == 'LONG':
        s = 'INT'
    elif type_name == 'TEXT':
        s = 'NCHAR(' + str(d['CHARACTER_LENGTH']) + ')'
    elif type_name == 'VARYING':
        if d['CHARACTER_LENGTH'] > 4000:
            s = 'NVARCHAR(max)'
        else:
            s = 'NVARCHAR(' + str(d['CHARACTER_LENGTH']) + ')'
    elif type_name == 'INT64':
        if d['FIELD_SUB_TYPE'] == 1:
            s = 'NUMERIC'
        else:
            s = 'DECIMAL'
        s += '('+str(d['FIELD_PRECISION'])+','+str(d['FIELD_SCALE']*-1)+')'
    elif type_name == 'BLOB' and d['FIELD_SUB_TYPE'] == 0:
        s = 'VARBINARY(max)'
    elif type_name == 'BLOB' and d['FIELD_SUB_TYPE'] == 1:
        s = 'VARCHAR(max)'
    elif type_name == 'DOUBLE':
        s = 'FLOAT'
    elif type_name == 'TIMESTAMP' or type_name == 'DATE':
        s = 'DATETIME'
    else:
        s = type_name

    return s

def fb_fieldtype_to_string(d):
    if d['FIELD_NAME'][:4] != 'RDB$':
        s = d['FIELD_NAME'].strip()     # DOMAIN's name
    else: # Builtin type
        type_name = d['TYPE_NAME'].strip()
        if type_name == 'SHORT':
            s = 'SMALLINT'
        elif type_name == 'LONG':
            s = 'INT'
        elif type_name == 'TEXT':
            s = 'NCHAR(' + str(d['CHARACTER_LENGTH']) + ')'
        elif type_name == 'VARYING':
            if d['CHARACTER_LENGTH'] > 4000:
                s = 'NVARCHAR(max)'
            else:
                s = 'NVARCHAR(' + str(d['CHARACTER_LENGTH']) + ')'
        elif type_name == 'INT64':
            if d['FIELD_SUB_TYPE'] == 1:
                s = 'NUMERIC'
            else:
                s = 'DECIMAL'
            s += '('+str(d['FIELD_PRECISION'])+','+str(d['FIELD_SCALE']*-1)+')'
        elif type_name == 'BLOB' and d['FIELD_SUB_TYPE'] == 0:
            s = 'VARBINARY(max)'
        elif type_name == 'BLOB' and d['FIELD_SUB_TYPE'] == 1:
            s = 'VARCHAR(max)'
        elif type_name == 'DOUBLE':
            s = 'FLOAT'
        elif type_name == 'TIMESTAMP' or type_name == 'DATE':
            s = 'DATETIME'
        else:
            s = type_name

    if not IsDBNull(d['DEFAULT_SOURCE']):
        s += ' ' + fbexpr_to_sqlexpr(d['DEFAULT_SOURCE'])

    if d['NULL_FLAG'] == 1:
        s += ' NOT NULL'

    return s

def copy_from_fb(host, login, password, db_name, conn_d, 
    set_default = False, foreign_keys = False, check_constraints = False, 
    need_data_copy=False, debug=False):
    global last_execute_sql

    smo = sqlutil.SqlSmo(host, login, password)
    sql_schema = smo.database(db_name)
    sql_db = sqlutil.SqlDatabase(host, login, password, db_name)
    sql_db.open()

    fb_db = fbutil.FbDatabase(conn_d)
    fb_db.open()

    for t in sql_schema.tables():
        for fk in t.foreign_keys(False):
            sqlStmt = 'alter table [%s] drop [%s]' % (str(t), fk[0])
            if debug:
                print sqlStmt
            sql_db.execute_noq(sqlStmt)
        
    for t in sql_schema.tables():
        sqlStmt = "drop table [" + str(t) + "]"
        if debug:
            print sqlStmt
        last_execute_sql = sqlStmt
        sql_db.execute_noq(sqlStmt)

    for t in sql_schema.domains():
        sqlStmt = "drop type " + str(t)
        if debug:
            print sqlStmt
        last_execute_sql = sqlStmt
        sql_db.execute_noq(sqlStmt)

    for u in fb_db.domains():
        sqlStmt = "create type %s from %s" % (
            u['NAME'].strip(),fb_domain_to_string(u))
        if debug:
            print sqlStmt
        last_execute_sql = sqlStmt
        sql_db.execute_noq(sqlStmt)

    for t in fb_db.tables():
        tab_name = t['NAME'].strip()
        pks = fb_db.primary_keys(tab_name)
        uks = fb_db.unique_keys(tab_name)
        sqlStmt = "create table [" + tab_name + "](\n"
        col_str = []
        for c in fb_db.columns(tab_name):
            s = '    [' + c['NAME'].strip() + '] '
            s += fb_fieldtype_to_string(c)
            if c['NAME'].strip() in uks:
                s += ' UNIQUE'
            col_str.append(s) 
        sqlStmt += ",\n".join(col_str)
        if len(pks):
            sqlStmt += ',\n    PRIMARY KEY ("' + '","'.join(pks) + '")'
        sqlStmt += ")"
        last_execute_sql = sqlStmt
        if debug:
            print sqlStmt
        sql_db.execute_noq(sqlStmt)

    if need_data_copy:
        for t in fb_db.tables():
            tab_name = t['NAME'].strip()
            insert_sql = '''insert into [%s] ([''' % (tab_name, )
            columns = [c['NAME'].strip() for c in fb_db.columns(tab_name)]
            insert_sql += '],['.join(columns)
            insert_sql += ''']) values ('''
            insert_sql += ','.join(['@'+c for c in columns])
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
                    params['@' + c] = v
                last_execute_sql = insert_sql + '\n' + str(params)
                sql_db.execute_noq(insert_sql, params)
            dr.Close()

    if foreign_keys:
        for t in fb_db.tables():
            tab_name = t['NAME'].strip()
            for fk in fb_db.foreign_keys(tab_name):
                sqlStmt = \
                'alter table [%s] add foreign key([%s]) references [%s]([%s])' \
                % (tab_name, fk['FIELD_NAME'].strip(), fk['REF_TABLE'].strip(), 
                                                    fk['REF_FIELD'].strip())
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                sql_db.execute_noq(sqlStmt)

    if check_constraints:
        for t in fb_db.tables():
            tab_name = t['NAME'].strip()
            for chk in fb_db.check_constraints(tab_name):
                sqlStmt = 'alter table [%s] add constraint [%s] %s' % \
                                    (tab_name, chk['CHECK_NAME'], 
                                    fbexpr_to_sqlexpr(chk['CHECK_SOURCE']))
                last_execute_sql = sqlStmt
                if debug:
                    print sqlStmt
                sql_db.execute_noq(sqlStmt)

    sql_db.close()
    fb_db.close()

if __name__ == '__main__':
    HOST = r'localhost\SQLEXPRESS'
    LOGIN = 'sa'
    PASSWD = 'secret'

    if len(sys.argv) == 2:
        testdir = sys.argv[1]
        if testdir[-1] != '\\':
            testdir = testdir + '\\'
    else:
        testdir = System.IO.Path.GetTempPath()
        
    print 'testdir=' + testdir

    targets = ['Northwind', 'pubs']
    for db_name in targets:
        conn_d = {
            'User' : 'SYSDBA',
            'Password' : 'masterkey',
            'DataSource' : 'localhost',
            'Database' : testdir + db_name + '.fdb',
            'Charset' : 'UNICODE_FSS', 
        }

        fb_db = copy_to_fb(HOST, LOGIN, PASSWD, db_name, conn_d, to_upper=False,
            set_default=True, foreign_keys=True, check_constraints=True,
            need_data_copy=True, debug=True)
        fb_db.close()
        copy_from_fb(HOST, LOGIN, PASSWD, db_name + '_fromfb', conn_d,
            set_default=True, foreign_keys=True, check_constraints=True,
            need_data_copy=True, debug=True)
    

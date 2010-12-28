##############################################################################
# Copyright (c) 2007-2009, Hajime Nakagami<nakagami@da2.so-net.ne.jp>
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
import System.IO
from System.Convert import IsDBNull
from System.Data import *
try:
    # Add reference to OracleClient data provider
    clr.AddReference("System.Data.OracleClient")
    from System.Data.OracleClient import *
    can_use_oracle = True
except: # Can't import System.Data.OracleClient
    can_use_oracle = False

fb_typestr_map = {
            'CHAR' : 'CHAR',
            'NCHAR' : 'CHAR',
            'VARCHAR' : 'VARCHAR',
            'NVARCHAR' : 'VARCHAR',
            'VARCHAR2' : 'VARCHAR',
            'NVARCHAR2' : 'VARCHAR',
            'BLOB' : 'BLOB SUB_TYPE 0',
            'CLOB' : 'BLOB SUB_TYPE 1',
            'NUMBER' : 'NUMERIC',
            'DATE' : 'TIMESTAMP',
            'TIMESTAMP' : 'TIMESTAMP',
        }

len_type = ('CHAR', 'NCHAR', 'VARCHAR', 'NVARCHAR', 'VARCHAR2', 'NVARCHAR2')
prescale_type = ('NUMBER')

def column_to_fbsql(d, to_upper, set_default):
    s = d['COLUMN_NAME']
    if to_upper:
        s = s.upper()
    s = '"' + s + '"'
    s += ' ' + fb_typestr_map[d['DATA_TYPE']]
    if d['DATA_TYPE'] in len_type:
        s += '(' + str(d['DATA_LENGTH']) + ')'
    elif d['DATA_TYPE'] in prescale_type:
        if IsDBNull(d['DATA_PRECISION']):
            pass
        else:
            if IsDBNull(d['DATA_SCALE']) or str(d['DATA_SCALE']) == '0':
                s += "(%s)" % (d['DATA_PRECISION'])
            else:
                s += "(%s,%s)" % (d['DATA_PRECISION'], d['DATA_SCALE'])
    if d['NULLABLE'] == 'N':
        s += ' NOT NULL'

    if set_default and not IsDBNull(d['DATA_DEFAULT']):
        s += ' DEFAULT ' + d['DATA_DEFAULT']

    return s


def column_sql(d):
    s = '"' + d['COLUMN_NAME'] + '" ' + d['DATA_TYPE']
    if d['DATA_TYPE'] in len_type:
        s += '(' + str(d['DATA_LENGTH']) + ')'
    elif d['DATA_TYPE'] in prescale_type:
        if IsDBNull(d['DATA_PRECISION']):
            pass
        else:
            if IsDBNull(d['DATA_SCALE']) or str(d['DATA_SCALE']) == '0':
                s += "(%s)" % (d['DATA_PRECISION'])
            else:
                s += "(%s,%s)" % (d['DATA_PRECISION'], d['DATA_SCALE'])
    if d['NULLABLE'] == 'N':
        s += ' NOT NULL'

    if not IsDBNull(d['DATA_DEFAULT']):
        s += ' DEFAULT ' + d['DATA_DEFAULT']
    return s


class OraDatabase(object):
    def __init__(self, host, login, passwd):
        conn = OracleConnection("Data Source=%s;User Id=%s;Password=%s;" % 
            (host, login, passwd))
        self.conn = conn
        self.owner = login.upper()

    def open(self):
        self.conn.Open()

    def close(self):
        self.conn.Close()

    def execute_noq(self, sqlStmt, params={}):
        cmd = OracleCommand(sqlStmt, self.conn)
        for k in params:
            cmd.Parameters.Add(OracleParameter(k, params[k]))
        return cmd.ExecuteNonQuery()

    def execute_sca(self, sqlStmt):
        return OracleCommand(sqlStmt, self.conn).ExecuteScalar()

    def execute(self, sqlStmt):
        return OracleCommand(sqlStmt, self.conn).ExecuteReader()

    def tables(self):
        return self.execute("select TABLE_NAME from USER_TABLES")

    def columns(self, tab_name):
        sqlStmt = """select COLUMN_NAME, DATA_TYPE, DATA_LENGTH, NULLABLE,
                DATA_DEFAULT, DATA_PRECISION, DATA_SCALE
            from USER_TAB_COLUMNS 
            where UPPER(TABLE_NAME)='%s' 
            order by COLUMN_ID""" % (tab_name.upper(),)
        return self.execute(sqlStmt)

    def create_fbsql(self, tab_name, to_upper, set_default):
        if to_upper:
            tab_name = tab_name.upper()
        sql = """create table "%s" (""" % (tab_name, )
        columns = self.columns(tab_name)
        sql += ','.join(['\n    ' + column_to_fbsql(c, to_upper, set_default) \
            for c in columns])

        if to_upper:
            pks = [str(c).upper() for c in self.primary_keys(tab_name)]
            uks = [str(c).upper() for c in self.unique_keys(tab_name)]
        else:
            pks = self.primary_keys(tab_name)
            uks = self.unique_keys(tab_name)
        if len(pks):
            sql += ',\n    PRIMARY KEY ("' + '","'.join(pks) + '")'
        if len(uks):
            sql += ',\n    UNIQUE ("' + '","'.join(uks) + '")'

        sql += "\n)"
        return sql

    def create_sql(self, tab_name):
        sql = """create table "%s" (""" % (tab_name, )
        columns = self.columns(tab_name)
        sql += ','.join(['\n    ' + column_sql(c) for c in columns])
        pks = self.primary_keys(tab_name)
        if len(pks):
            sql += ',\n    PRIMARY KEY ("' + '","'.join(pks) + '")'
        sql += "\n)"
        return sql

    def primary_keys(self, tab_name):
        sqlStmt = """select col.CONSTRAINT_NAME, col.COLUMN_NAME 
            from USER_CONSTRAINTS cons, USER_CONS_COLUMNS col
                where cons.CONSTRAINT_TYPE='P' and UPPER(cons.TABLE_NAME)='%s'
                    and cons.CONSTRAINT_NAME=col.CONSTRAINT_NAME
                order by col.POSITION """ % (tab_name.upper(), )
        return [r['COLUMN_NAME'] for r in self.execute(sqlStmt)]

    def unique_keys(self, tab_name):
        sqlStmt = """select col.CONSTRAINT_NAME, col.COLUMN_NAME 
            from USER_CONSTRAINTS cons, USER_CONS_COLUMNS col
                where cons.CONSTRAINT_TYPE='U' and UPPER(cons.TABLE_NAME)='%s'
                    and cons.CONSTRAINT_NAME=col.CONSTRAINT_NAME
                order by col.POSITION """ % (tab_name.upper(), )
        return [r['COLUMN_NAME'] for r in self.execute(sqlStmt)]

    def check_constraints(self, tab_name):
        d = {}
        sqlStmt = """select CONSTRAINT_NAME, SEARCH_CONDITION
            from USER_CONSTRAINTS cons
                where cons.CONSTRAINT_TYPE='C' 
                and UPPER(cons.TABLE_NAME)='%s'""" % (tab_name.upper(), )
        for r in self.execute(sqlStmt):
            d[r['CONSTRAINT_NAME']] = r['SEARCH_CONDITION']
        return d

    def foreign_keys(self, tab_name, to_upper):
        fks = {}
        sqlStmt = """select c.CONSTRAINT_NAME, c.TABLE_NAME, col.COLUMN_NAME,
            p.TABLE_NAME REF_TABLE, p_col.COLUMN_NAME REF_COLUMN
            from USER_CONSTRAINTS c,
                USER_CONSTRAINTS p,
                USER_CONS_COLUMNS col,
                USER_CONS_COLUMNS p_col
                where c.R_CONSTRAINT_NAME = p.CONSTRAINT_NAME
                    and c.CONSTRAINT_TYPE='R'
                    and p.CONSTRAINT_TYPE ='P'
                    and c.CONSTRAINT_NAME=col.CONSTRAINT_NAME
                    and c.TABLE_NAME=col.TABLE_NAME
                    and p.TABLE_NAME=p_col.TABLE_NAME
                    and p.CONSTRAINT_NAME=p_col.CONSTRAINT_NAME
                    and UPPER(c.TABLE_NAME) = '%s'
                order by p.TABLE_NAME, col.POSITION""" % (tab_name.upper(), )
        for r in self.execute(sqlStmt):
            d = fks.setdefault(r['CONSTRAINT_NAME'], {})
            if to_upper:
                d.setdefault('COLUMN_NAME', []).append(r['COLUMN_NAME'].upper())
                d['REF_TABLE'] = r['REF_TABLE'].upper()
                d.setdefault('REF_COLUMN', []).append(r['REF_COLUMN'].upper())
            else:
                d.setdefault('COLUMN_NAME', []).append(r['COLUMN_NAME'])
                d['REF_TABLE'] = r['REF_TABLE']
                d.setdefault('REF_COLUMN', []).append(r['REF_COLUMN'])
        return fks

def copy_db(src_host, src_login, src_password, 
            dest_host, dest_login, dest_password, debug=False):
    src_db = OraDatabase(src_host, src_login, src_password)
    src_db.open()

    dest_db = OraDatabase(dest_host, dest_login, dest_password)
    dest_db.open()

    # Create tables
    for t in src_db.tables():
        sqlStmt = src_db.create_sql(t['TABLE_NAME'])
        if debug:
            print sqlStmt
        try:
            dest_db.execute_noq(sqlStmt)
        except:
            if debug:
                print '---> Failed'

    src_table_names = [t['TABLE_NAME'] for t in src_db.tables()]

    # Drop foreign keys
    for t in dest_db.tables():
        if not t['TABLE_NAME'] in src_table_names:
            continue
        for k in dest_db.foreign_keys(t['TABLE_NAME'], False):
            sqlStmt = 'alter table "%s" drop constraint "%s"' % (t['TABLE_NAME'], k)
            if debug:
                print sqlStmt
            dest_db.execute_noq(sqlStmt)

    # Truncate tables
    for t in src_table_names:
        sqlStmt = 'truncate table "%s"' % (t, )
        if debug:
            print sqlStmt
        dest_db.execute_noq(sqlStmt)

    # Data copy
    for t in src_db.tables():
        columns = [c['COLUMN_NAME'] for c in src_db.columns(t['TABLE_NAME'])]
        insert_sql = '''insert into "%s" ("''' % (t['TABLE_NAME'], )
        insert_sql += '","'.join(columns)
        insert_sql += '''") values ('''
        insert_sql += ','.join([':'+c for c in columns])
        insert_sql += ''')'''

        sqlStmt = 'select * from "' + t['TABLE_NAME'] + '"'

        if debug:
            print sqlStmt
            print insert_sql

        dr = src_db.execute(sqlStmt)
        for r in dr:
            params = {}
            for c in columns:
                v = r[c]
                if type(v) == System.Int16 or type(v) == System.Byte:
                    v = int(v)
                params[c] = v
            dest_db.execute_noq(insert_sql, params)
        dr.Close()

    # Add foreign keys
    for t in src_db.tables():
        fks = src_db.foreign_keys(t['TABLE_NAME'], False)
        for k in fks:
            fk = fks[k]
            sqlStmt = 'alter table "' + t['TABLE_NAME'] + '" add foreign key("'
            sqlStmt += '","'.join(fk['COLUMN_NAME'])
            sqlStmt += '") references "%s"("' % (fk['REF_TABLE'], )
            sqlStmt += '","'.join(fk['REF_COLUMN'])
            sqlStmt += '")'
            if debug:
                print sqlStmt
            dest_db.execute_noq(sqlStmt)

if __name__ == '__main__':
    dest_db = OraDatabase('localhost', 'tiger', 'scott')
    dest_db.open()
    for t in dest_db.tables():
        sqlStmt = 'drop table "' + t['TABLE_NAME'] + '" cascade constraints'
        print sqlStmt
        dest_db.execute_noq(sqlStmt)
    dest_db.close()

    copy_db('localhost', 'scott', 'tiger', 
            'localhost', 'tiger', 'scott', debug=True)
    

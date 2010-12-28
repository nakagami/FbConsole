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
import sys, clr, re
import System.IO
from System.Convert import IsDBNull

# Append %ProgamFiles%\SQLite.NET\bin
from System import Environment as Env
slClientFolder = Env.GetFolderPath(Env.SpecialFolder.ProgramFiles)
slClientFolder += r'\SQLite.NET\bin'
if System.IO.Directory.Exists(slClientFolder):
    sys.path.append(slClientFolder)

try:
    # Add reference to SQLite data provider
    clr.AddReferenceToFile('System.Data.SQLite.dll')
    from System.Data.SQLite import *
    can_use_sqlite = True
except: # Can't import System.Data.SQLite
    can_use_sqlite = False
    
def DataTableToDictList(dt):
    keys = [str(col) for col in dt.Columns]
    a = []

    for r in dt.Rows:
        d = {}
        for k in keys:
            d[k] = r[k]
        a.append(d)

    return a


len_type = ('CHAR', 'VARCHAR')
prescale_type = ('NUMERIC', 'DECIMAL')
fb_typestr_map = {
            'NCHAR' : 'CHAR',
            'NVARCHAR' : 'VARCHAR',
            'VARCHAR2' : 'VARCHAR',
            'NVARCHAR2' : 'VARCHAR',
            'BLOB' : 'BLOB SUB_TYPE 0',
            'CLOB' : 'BLOB SUB_TYPE 1',
        }

def column_to_fbsql(d, ref_columns, to_upper, set_default):
    s = d['COLUMN_NAME']
    if to_upper:
        s = s.upper()
    s = '"' + s + '"'
    s += ' ' + fb_typestr_map.get(d['DATA_TYPE'].upper(), d['DATA_TYPE'])
    if d['DATA_TYPE'].upper() in len_type:
        s += '(' + str(d['CHARACTER_MAXIMUM_LENGTH']) + ')'
    elif d['DATA_TYPE'].upper() in prescale_type:
        if IsDBNull(d['NUMERIC_PRECISION']):
            pass
        else:
            if IsDBNull(d['NUMERIC_SCALE']) or str(d['NUMERIC_SCALE']) == '0':
                s += "(%s)" % (d['NUMERIC_PRECISION'])
            else:
                s += "(%s,%s)" % (d['NUMERIC_PRECISION'], d['NUMERIC_SCALE'])
    if not d['IS_NULLABLE']:
        s += ' NOT NULL'
    if d['COLUMN_NAME'] in ref_columns:
        s += ' UNIQUE'

    if set_default and d['COLUMN_HASDEFAULT']:
        s += ' DEFAULT ' + d['COLUMN_DEFAULT']

    return s

# Database connection wrapper
class SQLiteDatabase(object):
    def __init__(self, filename):
        self.filename = filename
        self.conn =  SQLiteConnection("Data Source=%s" % (self.filename,))

    def open(self):
        return self.conn.Open()

    def close(self):
        self.conn.Close()

    def table_adapter(self, tabname):
        return SQLiteDataAdapter('select * from ' + tabname, self.conn)

    def execute_noq(self, sqlStmt, params={}):
        cmd = SQLiteCommand(sqlStmt, self.conn)
        for k in params:
            cmd.Parameters.Add(SQLiteParameter(k, params[k]))
        return cmd.ExecuteNonQuery()

    def execute_sca(self, sqlStmt):
        return SQLiteCommand(sqlStmt, self.conn).ExecuteScalar()

    def execute(self, sqlStmt):
        return SQLiteCommand(sqlStmt, self.conn).ExecuteReader()

    def _schema(self, s):
        return DataTableToDictList(self.conn.GetSchema(s))

    def tables(self):
        return [t['TABLE_NAME'] for t in self._schema('Tables')]

    def columns(self, tab_name):
        return [c for c in self._schema('Columns') 
            if c['TABLE_NAME'] == tab_name]

    def create_fbsql(self, tab_name, to_upper, set_default):
        if to_upper:
            sql = """create table "%s" (""" % (tab_name.upper(), )
        else:
            sql = """create table "%s" (""" % (tab_name, )
        columns = self.columns(tab_name)
        ref_columns = self.ref_columns(tab_name)
        sql += ','.join(['\n    ' + 
            column_to_fbsql(c, ref_columns, to_upper, set_default) 
            for c in columns])

        if to_upper:
            pks = [str(c).upper() for c in self.primary_keys(tab_name)]
        else:
            pks = self.primary_keys(tab_name)
        if len(pks):
            sql += ',\n    PRIMARY KEY ("' + '","'.join(pks) + '")'

        sql += "\n)"
        return sql

    def primary_keys(self, tab_name):
        return [c['COLUMN_NAME'] for c in self._schema('Columns')
            if c['TABLE_NAME'] == tab_name and c['PRIMARY_KEY']]

    def unique_keys(self, tab_name):
        pks = self.primary_keys(tab_name)
        ui = [u['INDEX_NAME'] for u in self._schema('Indexes') if u['UNIQUE']]
        uks = []
        for u in self._schema('IndexColumns'):
            if u['TABLE_NAME'] == tab_name and u['INDEX_NAME'] in ui:
                if u['COLUMN_NAME'] in pks:
                    continue
                uks.append(u['COLUMN_NAME'])
        return uks

    def foreign_keys(self, tab_name, to_upper):
        fks = {}
        for r in self._schema('ForeignKeys'):
            if r['TABLE_NAME'] != tab_name:
                continue
            const_name = '_'.join(['FK', r['TABLE_NAME'], r['FKEY_TO_TABLE']])
            #const_name = r['CONSTRAINT_NAME']
            d = fks.setdefault(const_name, {})
            if to_upper:
                d.setdefault('COLUMN_NAME', []).append(
                        r['FKEY_FROM_COLUMN'].upper())
                d['REF_TABLE'] = r['FKEY_TO_TABLE'].upper()
                d.setdefault('REF_COLUMN', []).append(
                        r['FKEY_TO_COLUMN'].upper())
            else:
                d.setdefault('COLUMN_NAME', []).append(r['FKEY_FROM_COLUMN'])
                d['REF_TABLE'] = r['FKEY_TO_TABLE']
                d.setdefault('REF_COLUMN', []).append(r['FKEY_TO_COLUMN'])
        return fks

    def ref_columns(self, tab_name):
        ref_cols = []
        for r in self._schema('ForeignKeys'):
            if r['FKEY_TO_TABLE'] != tab_name:
                continue
            ref_cols.append(r['FKEY_TO_COLUMN'])
        return ref_cols

#------------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) == 2:
        testdir = sys.argv[1]
    else:
        testdir = System.IO.Path.GetTempPath()
        
    print 'testdir=' + testdir

    filename = testdir + r"\foo.db"
    print filename
    System.IO.File.Delete(filename)
    db = SQLiteDatabase(filename)
    db.open()

    db.execute_noq("""
        CREATE TABLE foo (
            a integer NOT NULL,
            b VARCHAR(30) NOT NULL UNIQUE,
            c VARCHAR(1024),
            d DECIMAL(16,2) DEFAULT 0.0,
            e DATE,
            f TIMESTAMP,
            g BLOB,
            PRIMARY KEY (a)
        );
    """)

    db.execute_noq("""
        CREATE TABLE bar (
            i INTEGER NOT NULL,
            j VARCHAR(30) NOT NULL,
            k VARCHAR(1024),
            PRIMARY KEY (i, j),
            FOREIGN KEY (j) REFERENCES foo(b) ON UPDATE CASCADE
        ); 

    """)
    db.execute_noq("insert into foo (a,b,c,d) values (1, 'ABC', 'a', 1.1)")
    db.execute_noq("insert into foo (a,b,c,d) values (2, 'DEF', 'b', 2.1)")

    to_upper = False
    for t in db.tables():
        print db.create_fbsql(t, to_upper, True)
        fks = db.foreign_keys(t, to_upper)
        for fk in fks:
            print fk,
            print fks[fk]
    db.close()


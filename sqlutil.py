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
from System.Data.SqlClient import *

try:
    # Append %ProgamFiles%\Microsoft SQL Server\90\SDK\Assemblies
    from System import Environment as Env
    sqlFolder = Env.GetFolderPath(Env.SpecialFolder.ProgramFiles)
    sqlFolder += r'\Microsoft SQL Server\90\SDK\Assemblies'
    if System.IO.Directory.Exists(sqlFolder):
        sys.path.append(sqlFolder)
    
    clr.AddReferenceToFile('Microsoft.SqlServer.ConnectionInfo.dll')
    clr.AddReferenceToFile('Microsoft.SqlServer.Smo.dll')
    clr.AddReferenceToFile('Microsoft.SqlServer.SqlEnum.dll')
    clr.AddReferenceToFile('Microsoft.SqlServer.SmoEnum.dll')
    
    from Microsoft.SqlServer.Management import Smo
    from Microsoft.SqlServer.Management.Common import ServerConnection
    
    fb_type_map = {
                Smo.SqlDataType.Bit : 'INTEGER',
                Smo.SqlDataType.Int : 'INTEGER',
                Smo.SqlDataType.SmallInt : 'SMALLINT',
                Smo.SqlDataType.TinyInt : 'SMALLINT',
                Smo.SqlDataType.Money : 'NUMERIC(18,4)',
                Smo.SqlDataType.SmallMoney : 'NUMERIC(18,4)',
                Smo.SqlDataType.Float : 'FLOAT',
                Smo.SqlDataType.Real : 'DOUBLE PRECISION',
                Smo.SqlDataType.DateTime : 'TIMESTAMP',
                Smo.SqlDataType.SmallDateTime : 'TIMESTAMP',
                Smo.SqlDataType.Char : 'CHAR',
                Smo.SqlDataType.NChar : 'CHAR',
                Smo.SqlDataType.VarChar : 'VARCHAR',
                Smo.SqlDataType.NVarChar : 'VARCHAR',
                Smo.SqlDataType.Text : 'BLOB SUB_TYPE 1',
                Smo.SqlDataType.NText : 'BLOB SUB_TYPE 1',
                Smo.SqlDataType.Binary : 'BLOB SUB_TYPE 0',
                Smo.SqlDataType.VarBinary : 'BLOB SUB_TYPE 0',
                Smo.SqlDataType.Image : 'BLOB SUB_TYPE 0',
                Smo.SqlDataType.Numeric : 'NUMERIC',
                Smo.SqlDataType.Decimal : 'DECIMAL',
            }
    can_use_sqlserver = True
except: # Can't import Smo
    can_use_sqlserver = False

fb_typestr_map = {
            'bit' : 'INTEGER',
            'int' : 'INTEGER',
            'smallint' : 'SMALLINT',
            'tinyint' : 'SMALLINT',
            'money' : 'NUMERIC(18,4)',
            'smallmoney' : 'NUMERIC(18,4)',
            'float' : 'FLOAT',
            'real' : 'DOUBLE PRECISION',
            'datetime' : 'TIMESTAMP',
            'smalldatetime' : 'TIMESTAMP',
            'char' : 'CHAR',
            'nchar' : 'CHAR',
            'varchar' : 'VARCHAR',
            'nvarchar' : 'VARCHAR',
            'text' : 'BLOB SUB_TYPE 1',
            'ntext' : 'BLOB SUB_TYPE 1',
            'binary' : 'BLOB SUB_TYPE 0',
            'varbinary' : 'BLOB SUB_TYPE 0',
            'image' : 'BLOB SUB_TYPE 0',
            'numeric' : 'NUMERIC',
            'decimal' : 'DECIMAL',
        }

len_type = ('char', 'nchar', 'varchar', 'nvarchar')
prescale_type = ('numeric', 'decimal')

def sqlexpr_to_fbexpr(expr, to_upper):
    d = {
        'GETDATE()':'CURRENT_DATE'
    }

    while expr[0] == '(' and expr[-1] == ')':
        expr = expr[1:-1]
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
        elif expr[i] == '[':
            s += '"'
            i += 1
            while expr[i] != ']' and i < len(expr):
                if to_upper:
                    s += expr[i].upper()
                else:
                    s += expr[i]
                i += 1
            s += '"'
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

class SqlSmoDomain(object):
    def __init__(self, smodomain):
        self.smodomain = smodomain

    def __str__(self):
        return self.smodomain.Name

    def script(self):
        sqltype = str(self.data_type())
        if str(self.data_type()) in len_type:
            sqltype += '(' + str(self.smodomain.MaxLength) + ')'
        elif str(self.data_type()) in prescale_type:
            sqltype += "(%i,%i)" % (self.smodomain.NumericPrecision, 
                            self.smodomain.NumericScale)
        if self.smodomain.Nullable:
            is_null = "NULL"
        else:
            is_null = "NOT NULL"
        return "execute sp_addtype %s, '%s', '%s'" % (self.smodomain.Name, 
                                                            sqltype, is_null)

    def data_type(self):
        return self.smodomain.SystemType

    def fb_type(self):
        fbtype = fb_typestr_map[self.data_type()]
        if self.smodomain.SystemType  in len_type:
            fbtype += '(' + str(self.smodomain.MaxLength) + ')'
        elif self.smodomain.SystemType in prescale_type:
            fbtype += "(%i,%i)" % (
                self.smodomain.NumericPrecision, self.smodomain.NumericScale)
        return fbtype

    def create_fbsql(self):
        sql = """CREATE DOMAIN %s AS %s""" % (self.__str__(), self.fb_type())

        return sql

class SqlSmoColumn(object):
    def __init__(self, smocolumn):
        self.smocolumn = smocolumn

    def __str__(self):
        return self.smocolumn.Name

    def data_type(self):
        return self.smocolumn.DataType

    def inpk(self):
        return self.smocolumn.InPrimaryKey

    def identity(self):
        if not self.smocolumn.Identity:
            return None
        return (self.smocolumn.IdentitySeed, self.smocolumn.IdentityIncrement)

    def set_identity_enable(self, f):
        self.smocolumn.Identity = f

    def fb_type(self):
        sql_dt = self.data_type().SqlDataType
        if sql_dt == Smo.SqlDataType.UserDefinedDataType:
            return self.data_type().Name
        fbtype = fb_type_map[sql_dt]
        if str(self.data_type()) in len_type:
            fbtype += '(' + str(self.data_type().MaximumLength) + ')'
        elif str(self.data_type()) in prescale_type:
            fbtype += "(%i,%i)" % (self.data_type().NumericPrecision, 
                            self.data_type().NumericScale)

        return fbtype

    def create_fbsql(self, to_upper, set_default):
        name = self.__str__()
        if to_upper:
            name = name.upper()
        sql = ' '.join(['"' + name + '"', self.fb_type()])
        if self.smocolumn.DefaultConstraint:
            sql += ' DEFAULT '
            sql += sqlexpr_to_fbexpr(self.smocolumn.DefaultConstraint.Text, to_upper)
        if not self.smocolumn.Nullable:
            sql += ' NOT NULL'
        return sql
            

class SqlSmoTable(object):
    def __init__(self, smotable):
        self.smotable = smotable

    def __str__(self):
        return self.smotable.Name

    def script(self):
        lines = []
        for ln in ('\n'.join(self.smotable.Script())).split('\n'):
            if ln[:13] == 'CREATE TABLE ':  # Owner to [dbo]
                ln = 'CREATE TABLE [dbo].[' + self.__str__() + ']('
            if ln:
                lines.append(ln)

        return '\n'.join(lines)

    def columns(self):
        cs = []
        for c in self.smotable.Columns:
            cs.append(SqlSmoColumn(c))
        return cs

    def columns_name(self):
        cn = []
        for c in self.smotable.Columns:
            cn.append(c.Name)
        return cn

    def checks(self, to_upper):
        r = []
        for chk in self.smotable.Checks:
            r.append([chk.Name, sqlexpr_to_fbexpr(chk.Text, to_upper)])
        return r

    def foreign_keys(self, to_upper, is_all=False):
        r = []
        for fk in self.smotable.ForeignKeys:
            if fk.IsEnabled or is_all:
                ref_tab = fk.ReferencedTable
                if to_upper:
                    ref_tab = ref_tab.upper()
                cols = []
                refs = []
                for c in fk.Columns:
                    if to_upper:
                        cols.append(c.Name.upper())
                        refs.append(c.ReferencedColumn.upper())
                    else:
                        cols.append(c.Name)
                        refs.append(c.ReferencedColumn)
                r.append([fk.Name, cols, ref_tab, refs])
        return r

    def create_fbsql(self, to_upper, set_default):
        name = self.__str__()
        if to_upper:
            name = name.upper()
        sql = """create table "%s" (""" % (name, )
        columns = self.columns()
        sql += ','.join(['\n    ' + c.create_fbsql(to_upper, set_default) \
            for c in columns])

        if to_upper:
            pks = [str(c).upper() for c in columns if c.inpk()]
        else:
            pks = [str(c) for c in columns if c.inpk()]
        if len(pks):
            sql += ',\n    PRIMARY KEY ("' + '","'.join(pks) + '")'

        sql += "\n)"
        return sql

    def insert_fbsql(self, to_upper):
        name = self.__str__()
        if to_upper:
            name = name.upper()
        sql = '''insert into "%s" ("''' % (name, )
        columns = self.columns()
        if to_upper:
            sql += '","'.join([str(c).upper() for c in columns])
        else:
            sql += '","'.join([str(c) for c in columns])
        sql += '''") values ('''
        sql += ','.join(['@'+str(c) for c in columns])
        sql += ''')'''
        return sql


class SqlSmoView(object):
    def __init__(self, smoview):
        self.smoview = smoview

    def __str__(self):
        return self.smoview.Name

    def script(self):
        return self.smoview.Script()

class SqlSmoDatabase(object):
    def __init__(self, smodb):
        self.smodb = smodb

    def __str__(self):
        return self.smodb.Name

    def tables(self):
        ts = []
        for t in self.smodb.Tables:
            if not t.IsSystemObject:
                ts.append(SqlSmoTable(t))
        return ts

    def views(self):
        vs = []
        for v in self.smodb.Views:
            if not v.IsSystemObject:
                vs.append(SqlSmoView(v))
        return vs

    def domains(self):
        ds = []
        for d in self.smodb.UserDefinedDataTypes:
            ds.append(SqlSmoDomain(d))
        return ds

class SqlSmo(object):
    def __init__(self, host, login, password):
        if login:
            conn = ServerConnection(host)
            conn.LoginSecure = False
            conn.Login = login
            conn.Password = password
            self.server = Smo.Server(conn)
        else:
            self.server = Smo.Server(host)

    def databases(self):
        ds = []
        for d in self.server.Databases:
            if not d.IsSystemObject:
                ds.append(SqlSmoDatabase(d))
        return ds

    def database(self, dbname):
        for d in self.server.Databases:
            if d.Name == dbname:
                return SqlSmoDatabase(d)

def sql_databases(host, login, password):
    if login and password:
        smo = SqlSmo(host, login, password)
    else:
        smo = SqlSmo(host)
    return [str(d) for d in smo.databases()]

class SqlDatabase(object):
    def __init__(self, host, login, passwd, db_name):
        conn = SqlConnection(
            "Data Source=%s;User ID=%s;Password=%s;Initial Catalog=%s" % 
            (host, login, passwd, db_name))
        self.conn = conn

    def open(self):
        self.conn.Open()

    def close(self):
        self.conn.Close()

    def execute_noq(self, sqlStmt, params={}):
        cmd = SqlCommand(sqlStmt, self.conn)
        for k in params:
            cmd.Parameters.Add(SqlParameter(k, params[k]))
        return cmd.ExecuteNonQuery()

    def execute_sca(self, sqlStmt):
        return SqlCommand(sqlStmt, self.conn).ExecuteScalar()

    def execute(self, sqlStmt):
        return SqlCommand(sqlStmt, self.conn).ExecuteReader()

def copy_db(src_host, src_login, src_password, src_db,
            dest_host, dest_login, dest_password, dest_db, debug=False):
    src_schema = SqlSmo(src_host, src_login, src_password).database(src_db)
    src_db = SqlDatabase(src_host, src_login, src_password, src_db)
    src_db.open()

    dest_schema = SqlSmo(dest_host, dest_login, dest_password).database(dest_db)
    dest_db = SqlDatabase(dest_host, dest_login, dest_password, dest_db)
    dest_db.open()

    # Create UserDefinedDataType
    for dom in src_schema.domains():
        if debug:
            print dom.script()
        try:
            dest_db.execute_noq(dom.script())
        except:
            if debug:
                print '---> Failed'

    # Create tables
    for t in src_schema.tables():
        sqlStmt = t.script()
        if debug:
            print sqlStmt
        try:
            dest_db.execute_noq(sqlStmt)
        except:
            if debug:
                print '---> Failed'

        pks = [str(c) for c in t.columns() if c.inpk()]
        sqlStmt = 'alter table [' + str(t) + '] add primary key(['
        sqlStmt += '],['.join(pks) 
        sqlStmt += '])' 
        if debug:
            print sqlStmt
        try:
            dest_db.execute_noq(sqlStmt)
        except:
            if debug:
                print '---> Failed'

    src_table_names = [str(t) for t in src_schema.tables()]

    # Nocheck constraint
    for t in src_table_names:
        sqlStmt = 'alter table [%s] nocheck constraint all' % (t,)
        if debug:
            print sqlStmt
        dest_db.execute_noq(sqlStmt)

    # Drop foreign keys
    for t in dest_schema.tables():
        if not str(t) in src_table_names:
            continue
        for fk in t.foreign_keys(False, is_all=True):
            sqlStmt = 'alter table [%s] drop [%s]' % (str(t), fk[0])
            if debug:
                print sqlStmt
            dest_db.execute_noq(sqlStmt)

    # Truncate tables
    for t in src_table_names:
        sqlStmt = 'truncate table [%s]' % (t, )
        if debug:
            print sqlStmt
        dest_db.execute_noq(sqlStmt)

    # Data copy
    for t in src_schema.tables():
        sqlStmt = "set identity_insert [%s] on" % (str(t), )
        if debug:
            print sqlStmt
        try:
            dest_db.execute_noq(sqlStmt)
        except:
            if debug:
                print '---> Failed'

        columns = [str(c) for c in t.columns()]
        insert_sql = '''insert into [%s] ([''' % (str(t), )
        insert_sql += '],['.join(columns)
        insert_sql += ''']) values ('''
        insert_sql += ','.join(['@'+c for c in columns])
        insert_sql += ''')'''

        sqlStmt = 'select * from [' + str(t) + ']'

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
                params['@' + c] = v
            dest_db.execute_noq(insert_sql, params)
        dr.Close()

        sqlStmt = "set identity_insert [%s] off" % (str(t), )
        if debug:
            print sqlStmt
        try:
            dest_db.execute_noq(sqlStmt)
        except:
            if debug:
                print '---> Failed'

        sqlStmt = "select ident_current('%s')" % (str(t), )
        if debug:
            print sqlStmt
        try:
            reseed = src_db.execute_sca(sqlStmt)
            sqlStmt = "dbcc checkident ('%s', RESEED, %d)" % (str(t), reseed)
            if debug:
                print sqlStmt
            dest_db.execute_noq(sqlStmt)
        except:
            if debug:
                print '---> Failed'

    # Add foreign keys
    for t in src_schema.tables():
        sqlStmt = 'alter table [%s] check constraint all' % (str(t),)
        if debug:
            print sqlStmt
        dest_db.execute_noq(sqlStmt)
        for fk in t.foreign_keys(False):
            sqlStmt = 'alter table [' + str(t) + '] add foreign key(['
            sqlStmt += '],['.join(fk[1])
            sqlStmt += ']) references [%s]([' % (fk[2], )
            sqlStmt += '],['.join(fk[3])
            sqlStmt += '])'
            if debug:
                print sqlStmt
            dest_db.execute_noq(sqlStmt)

if __name__ == '__main__':
    databases = sql_databases(r'localhost\SQLEXPRESS', 'sa', 'secret')
    print 'databases=', databases

    copy_db(r'localhost\SQLEXPRESS', 'sa', 'secret', 'pubs',
        r'localhost\SQLEXPRESS', 'sa', 'secret', 'pubs_dest', debug=True)

    copy_db(r'localhost\SQLEXPRESS', 'sa', 'secret', 'Northwind',
        r'localhost\SQLEXPRESS', 'sa', 'secret', 'Northwind_dest', debug=True)


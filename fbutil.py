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

# Append for FirebirdClient DLL
from System import Environment as Env
folders = (
    Env.GetFolderPath(Env.SpecialFolder.ProgramFiles) + r'\FirebirdClient 2.0',
    Env.GetFolderPath(Env.SpecialFolder.ProgramFiles) + r'\FirebirdClient',
)
for f in folders:
    if System.IO.Directory.Exists(f):
        sys.path.append(f)

# Add reference to Firebird data provider
clr.AddReferenceToFile('FirebirdSql.Data.FirebirdClient.dll')
from FirebirdSql.Data.FirebirdClient import *
from FirebirdSql.Data.Services import *
from FirebirdSql.Data.Isql import *

def create_generator_and_trigger_sql(tab_name, id_name, seed, inc):
    return '''create generator "%(tab_name)s_ID";
set generator "%(tab_name)s_ID" to %(seed)d;

set term !! ;
create trigger "%(tab_name)s_ID" for "%(tab_name)s"
before insert
as begin
  new."%(id_name)s" = gen_id("%(tab_name)s_ID",%(inc)d);
end
!!
set term ; !!''' % dict(tab_name=tab_name, id_name=id_name, seed=seed, inc=inc)

def expr_sql(name, value, t):
    if IsDBNull(value):
        if name:
            return '"' + name + '"' + " is NULL"
        else:
            return "NULL"

    if t == 'TEXT' or t == 'VARYING':
        v = "'" + value.replace("'", "''") + "'"
    elif t == 'DATE':
        v = "'" + str(value)[:10].replace('/', '-') + "'"
    elif t == 'TIME':
        v = "'" + str(value)[11:] + "'"
    elif t == 'TIMESTAMP':
        v = "'" + str(value) + "'"
    else:
        v = str(value)

    if name:
        return '"' + name + '"' + "=" + v
    else:
        return v

def make_dict_to_string(conn_d, ch=';', ignore_invalid_param=True):
    valid_param = ['User', 'Password', 'DataSource', 'Port', 'Database', 
        'PacketSize', 'Role', 'Dialect', 'Charset', 'ConnectionTimeout', 
        'Pooling', 'ConnectionLifeTime', 'MinPoolSize', 'MaxPoolSize', 
        'FetchSize', 'ServerType', 'IsolationLevel', 'ReturnRecordsAffected',
        'ContextConnection']
    d = {}
    if ignore_invalid_param:
        for k in conn_d:
            if k in valid_param:
                d[k] = conn_d[k]
    else:
        d.update(conn_d)
    return "".join([str(k) + '=' + str(conn_d[k]) + ch for k in d])

def make_string_to_dict(conn_s, ch=';'):
    d = {}
    for s in conn_s.split(ch):
        if s:
            k,v = s.split('=', 1)
            d[k] = v
    return d

def _print_handler(o, e):
    print e.Message

def fieldtype_to_string(d, 
    resolve_typename = True, with_null_flag = False, with_default = False):
    if resolve_typename and d['FIELD_NAME'][:4] != 'RDB$':
        s = d['FIELD_NAME'].strip()     # DOMAIN's name
    else: # Builtin type
        type_name = d['TYPE_NAME'].strip()
        if type_name == 'SHORT':
            s = 'SMALLINT'
        elif type_name == 'LONG':
            s = 'INTEGER'
        elif type_name == 'TEXT':
            s = 'CHAR(' + str(d['CHARACTER_LENGTH']) + ')'
        elif type_name == 'VARYING':
            s = 'VARCHAR(' + str(d['CHARACTER_LENGTH']) + ')'
        elif type_name == 'INT64':
            if d['FIELD_SUB_TYPE'] == 1:
                s = 'NUMERIC'
            else:
                s = 'DECIMAL'
            s += '('+str(d['FIELD_PRECISION'])+','+str(d['FIELD_SCALE']*-1)+')'
        elif type_name == 'BLOB':
            s = 'BLOB SUB_TYPE ' + str(d['FIELD_SUB_TYPE'])
        elif type_name == 'DOUBLE':
            s = 'DOUBLE PRECISION'
        else:
            s = type_name

    if with_default and not IsDBNull(d['DEFAULT_SOURCE']):
        s += ' ' + d['DEFAULT_SOURCE']
    if with_null_flag and d['NULL_FLAG'] == 1:
        s += ' NOT NULL'

    return s

def default_source_string(d):
    if not IsDBNull(d['DEFAULT_SOURCE']):
        s =  str(d['DEFAULT_SOURCE'])
    elif not IsDBNull(d['DOM_DEFAULT_SOURCE']): # DOMAIN
        s = str(d['DOM_DEFAULT_SOURCE']) + '(' + d['FIELD_NAME'].strip() + ')'
    else:
        s = ''
    return s

# Backup & Restore
def db_backup(conn_d, bkfile, meta_only=False, oh=None, bksize=2048):
    bk = FbBackup()
    bk.ConnectionString = make_dict_to_string(conn_d)
    bk.BackupFiles.Add(FbBackupFile(bkfile, bksize))
    bk.Verbose = True
    bk.Options = FbBackupFlags.IgnoreLimbo
    if meta_only:
        bk.Options |= FbBackupFlags.MetaDataOnly
    if oh:
        bk.ServiceOutput += ServiceOutputEventHandler(oh)
    bk.Execute()

def db_restore(conn_d, bkfile, ow = True, oh=None, bksize=2048, pgsize=4096):
    FbDatabase(conn_d).clear_pools()
    rs = FbRestore()
    rs.ConnectionString = make_dict_to_string(conn_d)
    rs.BackupFiles.Add(FbBackupFile(bkfile, bksize))
    rs.Verbose = True
    rs.PageSize = pgsize
    if ow:
        rs.Options = FbRestoreFlags.Create | FbRestoreFlags.Replace
    else:
        rs.Options = FbRestoreFlags.Create
    if oh:
        rs.ServiceOutput += ServiceOutputEventHandler(oh)
    rs.Execute()

# Log
def server_log(conn_d, oh=_print_handler):
    lg = FbLog()
    lg.ConnectionString = make_dict_to_string(conn_d)
    lg.ServiceOutput += ServiceOutputEventHandler(oh)
    lg.Execute()

# User
def user_add(conn_d, uName, password, first='', last='', middle=''):
    u = FbUserData()
    u.UserName = uName
    u.UserPassword = password
    u.FirstName = first
    u.LastName = last
    u.MiddleName = middle
    sec = FbSecurity()
    sec.ConnectionString = make_dict_to_string(conn_d)
    sec.AddUser(u)

def user_del(conn_d, uName):
    sec = FbSecurity()
    sec.ConnectionString = make_dict_to_string(conn_d)
    u = sec.DisplayUser(uName.upper())
    if u:
        sec.DeleteUser(u)

def user_mod(conn_d, uName, password=None, first=None, last=None, middle=None):
    sec = FbSecurity()
    sec.ConnectionString = make_dict_to_string(conn_d)
    u = sec.DisplayUser(uName.upper())
    if u:
        u.FirstName = first
        u.LastName = last
        u.MiddleName = middle
        u.UserPassword = password
        sec.ModifyUser(u)

def users_list(conn_d):
    sec = FbSecurity()
    sec.ConnectionString = make_dict_to_string(conn_d)
    r = []
    for u in  sec.DisplayUsers():
        r.append({'NAME': u.UserName,
                'FIRST': u.FirstName, 
                'MIDDLE': u.MiddleName, 
                'LAST': u.LastName})
    return r

# Database connection wrapper
class FbDatabase(object):
    def __init__(self, conn_d, create_flag = False,
                page_size = 4096, forced_writes = True, over_write = False):
        self.conn_d = conn_d
        if not 'Pooling' in conn_d:
            conn_d['Pooling'] = False
        s = "".join([str(k)+'='+str(self.conn_d[k])+';' for k in self.conn_d])
        self.conn =  FbConnection(s)
        if create_flag:
            self.conn.CreateDatabase(s, page_size, forced_writes, over_write)

    def open(self):
        return self.conn.Open()

    def close(self):
        self.conn.Close()

    def table_adapter(self, tabname):
        return FbDataAdapter('select * from "' + tabname + '"', self.conn)

    def clear_pools(self):
        self.conn.ClearAllPools()

    def execute_batch(self, sqlStmt, event_handler = None):
        script = FbScript(System.IO.StringReader(sqlStmt))
        script.Parse()
        b = FbBatchExecution(self.conn, script)
        if event_handler:
            b.CommandExecuted += event_handler
        return b.Execute()

    def execute_noq(self, sqlStmt, params={}):
        cmd = FbCommand(sqlStmt, self.conn)
        for k in params:
            cmd.Parameters.Add(FbParameter(k, params[k]))
        return cmd.ExecuteNonQuery()

    def execute_sca(self, sqlStmt):
        return FbCommand(sqlStmt, self.conn).ExecuteScalar()

    def execute(self, sqlStmt):
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def info(self):
        d = {'Version': self.conn.ServerVersion,
            'Packet Size' : self.conn.PacketSize,
            'Connection Timeout' : self.conn.ConnectionTimeout,
            'DataSource' : self.conn.DataSource,
            'Database' : self.conn.Database,
        }
        sqlStmt = '''select rdb$character_set_name from rdb$database'''
        d['CHARACTER_SET'] = FbCommand(sqlStmt, self.conn).ExecuteScalar()
        return d

    def tables(self, system_flag=0):
        sqlStmt = '''select rdb$relation_name NAME,
            rdb$owner_name OWNER,
            rdb$description DESCRIPTION
            from rdb$relations 
            where rdb$system_flag=%d and rdb$view_source is null
            order by rdb$relation_name''' % system_flag
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def views(self, name=None):
        sqlStmt = '''select rdb$relation_name NAME,
            rdb$owner_name OWNER,
            rdb$description DESCRIPTION
            from rdb$relations
            where rdb$flags=1 and rdb$view_source is not null
            order by rdb$relation_name'''
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def view_source(self, name):
        sqlStmt = '''select rdb$view_source VIEW_SOURCE
            from rdb$relations
            where rdb$relation_name='%s' and 
                rdb$flags=1 and rdb$view_source is not null
            ''' % (name, )
        return FbCommand(sqlStmt, self.conn).ExecuteScalar()

    def roles(self):
        sqlStmt = '''select rdb$role_name NAME, rdb$owner_name OWNER
            from rdb$roles order by rdb$role_name'''
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def grant_users(self, relation_name):
        sqlStmt = '''select rdb$user NAME, rdb$privilege PRIVILEGE,
            rdb$grant_option GRANT_OPTION, rdb$field_name FIELD_NAME
            from rdb$user_privileges where rdb$relation_name='%s'
            order by rdb$user ''' % (relation_name, )
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def domains(self, dom_name=None):
        if dom_name:
            sqlStmt = '''select B.rdb$field_name NAME,
                C.rdb$type_name TYPE_NAME,
                B.rdb$field_sub_type FIELD_SUB_TYPE, 
                B.rdb$field_precision FIELD_PRECISION,
                B.rdb$field_scale FIELD_SCALE, 
                B.rdb$character_length "CHARACTER_LENGTH",
                B.rdb$field_name FIELD_NAME,
                B.rdb$validation_source VALIDATION_SOURCE,
                B.rdb$default_source DEFAULT_SOURCE,
                B.rdb$description DESCRIPTION
                from rdb$fields B, rdb$types C 
                where C.rdb$field_name='RDB$FIELD_TYPE'
                    and B.rdb$field_type=C.rdb$type
                    and B.rdb$field_name ='%s' ''' % (dom_name,)
            cmd = FbCommand(sqlStmt, self.conn).ExecuteReader()
            cmd.Read()
        else:
            sqlStmt = '''select B.rdb$field_name NAME,
                C.rdb$type_name TYPE_NAME,
                B.rdb$field_sub_type FIELD_SUB_TYPE, 
                B.rdb$field_precision FIELD_PRECISION,
                B.rdb$field_scale FIELD_SCALE, 
                B.rdb$character_length "CHARACTER_LENGTH",
                B.rdb$field_name FIELD_NAME,
                B.rdb$validation_source VALIDATION_SOURCE,
                B.rdb$default_source DEFAULT_SOURCE,
                B.rdb$description DESCRIPTION
                from rdb$fields B, rdb$types C 
                where C.rdb$field_name='RDB$FIELD_TYPE'
                    and B.rdb$field_type=C.rdb$type
                    and not B.rdb$field_name like 'RDB$%'
                order by B.rdb$field_name'''
            return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def exceptions(self):
        sqlStmt = '''select rdb$exception_name NAME,
            rdb$message MESSAGE_STRING, rdb$description DESCRIPTION
            from rdb$exceptions 
            order by rdb$exception_number'''
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def columns(self, table_name):
        sqlStmt = '''select A.rdb$field_name NAME,
            A.rdb$null_flag NULL_FLAG, 
            A.rdb$default_source DEFAULT_SOURCE,
            A.rdb$description DESCRIPTION,
            C.rdb$type_name TYPE_NAME,
            B.rdb$field_sub_type FIELD_SUB_TYPE, 
            B.rdb$field_precision FIELD_PRECISION,
            B.rdb$field_scale FIELD_SCALE, 
            B.rdb$character_length "CHARACTER_LENGTH",
            B.rdb$field_name FIELD_NAME,
            B.rdb$default_source DOM_DEFAULT_SOURCE, 
            B.rdb$validation_source VALIDATION_SOURCE
            from rdb$relation_fields A, rdb$fields B, rdb$types C
            where C.rdb$field_name='RDB$FIELD_TYPE'
                and A.rdb$field_source = B.rdb$field_name
                and B.rdb$field_type=C.rdb$type 
                and  upper(A.rdb$relation_name) = '%s'
            order by A.rdb$field_position, A.rdb$field_name
            ''' % (table_name.upper(), )
        return FbCommand(sqlStmt, self.conn).ExecuteReader()
    
    def key_constraints_and_index(self, table_name):
        sqlStmt = '''select 
            A.rdb$index_name INDEX_NAME, 
            A.rdb$index_id INDEX_ID, 
            A.rdb$unique_flag UNIQUE_FLAG,
            A.rdb$index_inactive INACT,
            A.rdb$statistics STATISTIC,
            A.rdb$foreign_key FOREIGN_KEY, 
            B.rdb$field_name FIELD_NAME, 
            C.rdb$constraint_type CONST_TYPE, 
            C.rdb$constraint_name CONST_NAME,
            D.rdb$update_rule UPDATE_RULE, 
            D.rdb$delete_rule DELETE_RULE
            from rdb$indices A
                left join rdb$index_segments B
                        on A.rdb$index_name=B.rdb$index_name 
                left join rdb$relation_constraints C 
                        on A.rdb$index_name=C.rdb$index_name
                left join rdb$ref_constraints D 
                        on C.rdb$constraint_name=D.rdb$constraint_name
            where A.rdb$relation_name='%s' ''' % table_name
        rows = FbCommand(sqlStmt, self.conn).ExecuteReader()
    
        d = {}
        for row in rows:
            if not d.has_key(row['INDEX_ID']):
                const_type = row['CONST_TYPE']
                if not IsDBNull(const_type):
                    const_type = const_type.strip()
                const_name = row['CONST_NAME']
                if not IsDBNull(const_name):
                    const_name = const_name.strip()
                update_rule = row['UPDATE_RULE']
                if not IsDBNull(update_rule):
                    update_rule = update_rule.strip()
                delete_rule = row['DELETE_RULE']
                if not IsDBNull(delete_rule):
                    delete_rule = delete_rule.strip()
                d[row['INDEX_ID']] = {
                    'INDEX_NAME': row['INDEX_NAME'].strip(), 
                    'UNIQUE_FLAG': row['UNIQUE_FLAG'],
                    'INACT' : row['INACT'],
                    'STATISTICS' : row['STATISTIC'],
                    'CONST_TYPE': const_type, 
                    'CONST_NAME': const_name,
                    'UPDATE_RULE': update_rule,
                    'DELETE_RULE': delete_rule,
                    'FIELD_NAME': [],
                }

                if not IsDBNull(row['FOREIGN_KEY']):
                    d[row['INDEX_ID']]['FOREIGN_KEY'] = \
                            self._references(row['FOREIGN_KEY'].strip())
                else:
                    d[row['INDEX_ID']]['FOREIGN_KEY'] = ''
            d[row['INDEX_ID']]['FIELD_NAME'].append(row['FIELD_NAME'].strip())
        # convert dict to array. Key value (INDEX_ID) is not need.
        a = []
        for k in d:
            a.append(d[k])
        return a
    
    def _references(self, index_name):
        sqlStmt = '''select 
            A.rdb$relation_name RELATION_NAME, 
            B.rdb$field_name FIELD_NAME 
            from rdb$indices A, rdb$index_segments B
            where A.rdb$index_name='%s' 
                and A.rdb$index_name=b.rdb$index_name''' % index_name
        rows = FbCommand(sqlStmt, self.conn).ExecuteReader()
        d = []
        for r in rows:
            table_name = r['RELATION_NAME'].strip()
            d.append(r['FIELD_NAME'].strip())
    
        return (index_name, table_name, d)  #index,table,[fields]
    
    def check_constraints(self, tabname):
        sqlStmt = '''select 
            A.rdb$constraint_name CHECK_NAME, 
            C.rdb$trigger_source CHECK_SOURCE 
            from rdb$relation_constraints A, rdb$check_constraints B, 
                rdb$triggers C
            where 
                A.rdb$constraint_type='CHECK' 
                and A.rdb$constraint_name = B.rdb$constraint_name 
                and B.rdb$trigger_name = C.rdb$trigger_name 
                and C.rdb$trigger_type=1
                and upper(A.rdb$relation_name) = '%s' ''' % tabname.upper()
        a = []
        for row in FbCommand(sqlStmt, self.conn).ExecuteReader():
            a.append({'CHECK_NAME': row['CHECK_NAME'].strip(),
                        'CHECK_SOURCE': row['CHECK_SOURCE']})
        return a

    def constraints(self, table_name):
        a = []
        key_constraints = self.key_constraints_and_index(table_name)
        for const_type in ('PRIMARY KEY', 'UNIQUE'):
            for r in key_constraints:
                if r['CONST_TYPE'] == const_type:
                    d = {}
                    d['NAME'] = r['CONST_NAME']
                    d['TYPE'] = r['CONST_TYPE']
                    d['FIELDS'] = ','.join(r['FIELD_NAME'])
                    d['CONDITION'] = ''
                    a.append(d)
        for r in key_constraints:
            if r['CONST_TYPE'] != 'FOREIGN KEY':
                continue
            d = {}
            d['TYPE'] = r['CONST_TYPE']
            d['NAME'] = r['CONST_NAME']
            d['FIELDS'] = ','.join(r['FIELD_NAME'])
            d['CONDITION'] = 'REFERENCES ' + r['FOREIGN_KEY'][1]
            d['CONDITION'] += '(' + ','.join(r['FOREIGN_KEY'][2]) + ')'
            if r['UPDATE_RULE'] != 'RESTRICT':
                d['CONDITION'] += ' ON UPDATE ' + r['UPDATE_RULE']
            if r['DELETE_RULE'] != 'RESTRICT':
                d['CONDITION'] += ' ON DELETE ' + r['DELETE_RULE']
            a.append(d)
            
        check_constraints = self.check_constraints(table_name)
        for r in check_constraints:
            d = {}
            d['TYPE'] = 'CHECK'
            d['NAME'] = r['CHECK_NAME']
            d['FIELDS'] = ''
            d['CONDITION'] = r['CHECK_SOURCE']
            a.append(d)

        return a

    def _keys(self, tname, key_type):
        sqlStmt = '''select 
            a.rdb$index_name INDEX_NAME, 
            b.rdb$field_name F
            from rdb$indices A
                left join rdb$index_segments B
                        on A.rdb$index_name=B.rdb$index_name 
                left join rdb$relation_constraints C 
                        on A.rdb$index_name=C.rdb$index_name
                left join rdb$ref_constraints D 
                        on C.rdb$constraint_name=D.rdb$constraint_name
            where upper(A.rdb$relation_name)='%s' 
                and c.rdb$constraint_type='%s' 
            ''' % (tname.upper(), key_type)
        return [r['F'].strip() \
                    for r in FbCommand(sqlStmt, self.conn).ExecuteReader()]

    def primary_keys(self, tname):
        return self._keys(tname, 'PRIMARY KEY')

    def unique_keys(self, tname):
        return self._keys(tname, 'UNIQUE')
    
    def foreign_keys(self, tname):
        sqlStmt = '''select
            A.rdb$index_name INDEX_NAME,
            A.rdb$foreign_key FOREING_KEY,
            B.rdb$field_name FIELD_NAME,
            C.rdb$constraint_type CONST_TYPE, 
            C.rdb$constraint_name CONST_NAME,
            D.rdb$update_rule UPDATE_RULE, 
            D.rdb$delete_rule DELETE_RULE,
            A2.rdb$relation_name REF_TABLE,
            B2.rdb$field_name REF_FIELD
            from rdb$indices A
                left join rdb$index_segments B
                        on A.rdb$index_name=B.rdb$index_name 
                left join rdb$relation_constraints C 
                        on A.rdb$index_name=C.rdb$index_name
                left join rdb$ref_constraints D 
                        on C.rdb$constraint_name=D.rdb$constraint_name
                ,
                rdb$indices A2, rdb$index_segments B2
            where upper(A.rdb$relation_name)='%s' 
                and A2.rdb$index_name=A.rdb$foreign_key
                and A2.rdb$index_name=B2.rdb$index_name
        ''' % tname.upper()
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def referenced_columns(self, tname):
        sqlStmt = '''select 
            B2.rdb$field_name FIELD_NAME,
            C.rdb$constraint_name CONST_NAME,
            A.rdb$relation_name REFERENCED_TABLE, 
            B.rdb$field_name REFERENCED_FIELD
            from rdb$indices A
                left join rdb$relation_constraints C 
                        on A.rdb$index_name=C.rdb$index_name,
                rdb$index_segments B, 
                rdb$indices A2, rdb$index_segments B2
            where A.rdb$index_name=B.rdb$index_name
                and A2.rdb$index_name=B2.rdb$index_name
                and A.rdb$foreign_key = A2.rdb$index_name
                and A2.rdb$relation_name = '%s'
            ''' % tname.upper()
        return FbCommand(sqlStmt, self.conn).ExecuteReader()
    
    def generators(self):
        sqlStmt = '''select 
            rdb$generator_name NAME from rdb$generators 
            where rdb$system_flag is null or rdb$system_flag = 0 
            order by rdb$system_flag, rdb$generator_name'''
        r = []
        for row in FbCommand(sqlStmt, self.conn).ExecuteReader():
            v = FbCommand(
                '''select gen_id("%s",0) V from rdb$database''' % row['NAME'],
                self.conn).ExecuteScalar()
            r.append({'NAME': row['NAME'].strip(), 'COUNT': v})
        return r

    def get_generator_id(self, gen_name):
        sqlStmt = 'select gen_id(' + gen_name + ', 0) V from rdb$database'
        return FbCommand(sqlStmt, self.conn).ExecuteScalar()
    
    def triggers(self, tabname=None):
        if tabname:
            sqlStmt = '''select 
                rdb$trigger_name NAME, 
                rdb$relation_name TABLE_NAME,
                rdb$trigger_sequence SEQUENCE, 
                rdb$trigger_type TRIGGER_TYPE, 
                rdb$trigger_inactive INACT
                    from rdb$triggers
                    where (rdb$system_flag is null or rdb$system_flag = 0)
                        and rdb$relation_name='%s'
                    order by rdb$relation_name, rdb$trigger_type, 
                        rdb$trigger_sequence
            ''' % tabname
        else:
            sqlStmt = '''select 
                rdb$trigger_name NAME, 
                rdb$relation_name TABLE_NAME,
                rdb$trigger_sequence SEQUENCE, 
                rdb$trigger_type TRIGGER_TYPE, 
                rdb$trigger_inactive INACT
                    from rdb$triggers
                    where (rdb$system_flag is null or rdb$system_flag = 0)
                    order by rdb$relation_name, rdb$trigger_type,
                        rdb$trigger_sequence'''
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def trigger_source(self, name):
        sqlStmt = '''select 
            rdb$relation_name TABLE_NAME,
            rdb$trigger_sequence SEQUENCE, 
            rdb$trigger_type TRIGGER_TYPE, 
            rdb$trigger_source SOURCE, 
            rdb$trigger_inactive INACT
                from rdb$triggers
                where rdb$trigger_name='%s' ''' % (name, )
        cmd = FbCommand(sqlStmt, self.conn).ExecuteReader()
        cmd.Read()
        return cmd

    def procedures(self):
        sqlStmt = '''select rdb$procedure_name NAME, 
            rdb$description DESCRIPTION
            from rdb$procedures order by rdb$procedure_name'''
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def procedure_source(self, name):
        sqlStmt = '''select rdb$procedure_name NAME, 
                rdb$procedure_source SOURCE,
                rdb$description DESCRIPTION
            from rdb$procedures
            where rdb$procedure_name='%s' ''' % (name,)
        r = []
        for row in FbCommand(sqlStmt, self.conn).ExecuteReader():
            sqlStmt = '''select 
                A.rdb$parameter_name NAME, 
                A.rdb$description DESCRIPTION,
                C.rdb$type_name TYPE_NAME, 
                B.rdb$field_sub_type FIELD_SUB_TYPE, 
                B.rdb$field_precision FIELD_PRECISION,
                B.rdb$field_scale FIELD_SCALE, 
                B.rdb$character_length "CHARACTER_LENGTH",
                B.rdb$field_name FIELD_NAME,
                B.rdb$null_flag NULL_FLAG, B.rdb$default_source DEFAULT_SOURCE
                from rdb$procedure_parameters A, rdb$fields B, rdb$types C
                where C.rdb$field_name='RDB$FIELD_TYPE' 
                    and A.rdb$field_source = B.rdb$field_name 
                    and A.rdb$parameter_type = 0
                    and B.rdb$field_type=C.rdb$type 
                    and  A.rdb$procedure_name='%s'
                order by A.rdb$parameter_number''' % row['NAME']
            in_params = []
            for p in FbCommand(sqlStmt, self.conn).ExecuteReader():
                in_params.append({ 'NAME': p['NAME'].strip(),
                    'DESCRIPTION': p['DESCRIPTION'],
                    'TYPE_NAME': p['TYPE_NAME'],
                    'FIELD_SUB_TYPE': p['FIELD_SUB_TYPE'],
                    'FIELD_PRECISION': p['FIELD_PRECISION'],
                    'FIELD_SCALE': p['FIELD_SCALE'],
                    'CHARACTER_LENGTH': p['CHARACTER_LENGTH'],
                    'FIELD_NAME' : p['FIELD_NAME'],
                    'NULL_FLAG': p['NULL_FLAG'],
                    'DEFAULT_SOURCE': p['DEFAULT_SOURCE'],
                })
    
            sqlStmt = ''' select 
                A.rdb$parameter_name NAME, 
                A.rdb$description DESCRIPTION,
                C.rdb$type_name TYPE_NAME,
                B.rdb$field_sub_type FIELD_SUB_TYPE, 
                B.rdb$field_precision FIELD_PRECISION,
                B.rdb$field_scale FIELD_SCALE, 
                B.rdb$character_length "CHARACTER_LENGTH",
                B.rdb$field_name FIELD_NAME,
                B.rdb$null_flag NULL_FLAG, B.rdb$default_source DEFAULT_SOURCE
                from rdb$procedure_parameters A, rdb$fields B, rdb$types C
                where C.rdb$field_name='RDB$FIELD_TYPE' 
                    and A.rdb$field_source = B.rdb$field_name 
                    and A.rdb$parameter_type = 1
                    and B.rdb$field_type=C.rdb$type 
                    and  A.rdb$procedure_name='%s'
                order by A.rdb$parameter_number''' % row['NAME']
            out_params = []
            for p in FbCommand(sqlStmt, self.conn).ExecuteReader():
                out_params.append({ 'NAME': p['NAME'].strip(),
                    'DESCRIPTION': p['DESCRIPTION'],
                    'TYPE_NAME': p['TYPE_NAME'],
                    'FIELD_SUB_TYPE': p['FIELD_SUB_TYPE'],
                    'FIELD_PRECISION': p['FIELD_PRECISION'],
                    'FIELD_SCALE': p['FIELD_SCALE'],
                    'CHARACTER_LENGTH': p['CHARACTER_LENGTH'],
                    'FIELD_NAME' : p['FIELD_NAME'],
                    'NULL_FLAG': p['NULL_FLAG'],
                    'DEFAULT_SOURCE': p['DEFAULT_SOURCE'],
                })
    
            r.append({'NAME': row['NAME'].strip(),
                    'DESCRIPTION': row['DESCRIPTION'],
                    'SOURCE': row['SOURCE'],
                    'IN_PARAMS': in_params,
                    'OUT_PARAMS':out_params})
        return r[0] # only 1 record.

    def function_names(self):
        sqlStmt = '''select rdb$function_name FUNCTION_NAME, 
            rdb$entrypoint ENTRYPOINT,
            rdb$module_name LIBNAME,
            rdb$description DESCRIPTION
            from rdb$functions 
            order by rdb$function_name
            '''
        return FbCommand(sqlStmt, self.conn).ExecuteReader()

    def copy_table(self, oname, nname, schema_only = False):
        if len(re.findall('^[A-Za-z][A-Za-z0-9_]*$', nname)) == 0:
            return False
        nname = nname.upper()
        # Table columns
        sqlStmt = "create table " + nname + "(\n"
        sqlStmt += ",\n".join([c['NAME'].strip() + ' ' + 
            fieldtype_to_string(c, with_null_flag=True, with_default=True)
            for c in self.columns(oname)])
        sqlStmt += ")"
        self.execute_noq(sqlStmt)

        # Data
        if not schema_only:
            self.execute_noq("insert into %s select * from %s" % (nname, oname))

        # Primary key
        pks = self.primary_keys(oname)
        if pks:
            sqlStmt = "alter table " + nname + " add primary key("
            sqlStmt += ",".join(pks)
            sqlStmt += ")"
            self.execute_noq(sqlStmt)

        # Foreing keys
        for fk in self.foreign_keys(oname):
            sqlStmt = \
                'alter table "%s" add foreign key("%s") references "%s"("%s")' \
                % (nname, fk['FIELD_NAME'].strip(), fk['REF_TABLE'].strip(), 
                                                    fk['REF_FIELD'].strip())
            if fk['UPDATE_RULE'].strip() != 'RESTRICT':
                sqlStmt += ' on update ' + fk['UPDATE_RULE']
            if fk['DELETE_RULE'].strip() != 'RESTRICT':
                sqlStmt += ' on delete ' + fk['DELETE_RULE']
            self.execute_noq(sqlStmt)

        n = 1
        # Unique constraints
        for ucol in self.unique_keys(oname):
            while (self.execute_sca('''select count(*) 
                from rdb$relation_constraints
                where rdb$constraint_name='INTEG_%d' ''' % (n,))):
                n = n + 1
            sqlStmt = "alter table %s add constraint INTEG_%d UNIQUE(%s)" % \
                (nname, n, ucol)
            self.execute_noq(sqlStmt)
        # Check constraints
        for c in self.check_constraints(oname):
            while (self.execute_sca('''select count(*) 
                from rdb$relation_constraints
                where rdb$constraint_name='INTEG_%d' ''' % (n,))):
                n = n + 1
            sqlStmt = "alter table %s add constraint INTEG_%d %s" % \
                (nname, n, c['CHECK_SOURCE'])
            self.execute_noq(sqlStmt)

        return True


    def set_not_null(self, table_name, column_name, not_null, check_flag=True):
        if check_flag and not_null == True:
            sqlStmt = '''select count(*) c from %s 
                        where %s is null''' % (table_name, column_name)
            n = FbCommand(sqlStmt, self.conn).ExecuteScalar()
            if n != 0:
                return "%s have %d NULL record(s)." % (column_name, n)
        if check_flag and not_null == False:
            sqlStmt = '''select A.rdb$index_name INDEX_NAME
                from rdb$indices A, rdb$index_segments B
                where A.rdb$index_name=B.rdb$index_name
                    and A.rdb$relation_name = '%s'
                    and B.rdb$field_name = '%s' 
                    ''' % (table_name.upper(), column_name.upper())
            cmd = FbCommand(sqlStmt, self.conn).ExecuteReader()
            if cmd.Read():
                return column_name + " has index '" + cmd['INDEX_NAME'].strip() + "'."

        table_name = table_name.upper()
        column_name = column_name.upper()
        if not_null:
            flag = '1'
        else:
            flag = 'NULL'
        sqlStmt = ''' update rdb$relation_fields set rdb$null_flag = %s
            where rdb$field_name = '%s' 
            and rdb$relation_name='%s' ''' % (flag, column_name, table_name)
        FbCommand(sqlStmt, self.conn).ExecuteNonQuery()
        return None

    def reorder_fields(self, name, fields):
        for i in range(len(fields)):
            s = "alter table %s alter %s position %d" % (name, fields[i], i+1)
            FbCommand(s, self.conn).ExecuteNonQuery()
        
    def write_description(self, category, description, name, name2=None):
        description = description.replace('\\', '\\\\')
        description = description.replace("'", "''")

        if category=='domain':
            sqlStmt = '''update rdb$fields set rdb$description='%s' 
                where rdb$field_name='%s' and rdb$validation_source is not null
                ''' % (description, name.upper())
        elif category=='role':
            sqlStmt = '''update rdb$roles set rdb$description='%s'
                where rdb$role_name='%s' 
                ''' % (description, name.upper())
        elif category=='table':
            sqlStmt = '''update rdb$relations set rdb$description='%s'
                where rdb$relation_name='%s' 
                ''' % (description, name.upper())
        elif category=='column':
            sqlStmt = ''' update rdb$relation_fields set rdb$description='%s'
                where rdb$relation_name='%s' and rdb$field_name='%s'
                ''' %(description, name.upper(), name2.upper())
        elif category=='exception':
            sqlStmt = '''update rdb$exceptions set rdb$description='%s'
                where rdb$exception_name='%s' 
                ''' % (description, name.upper())
        elif category=='procedure':
            sqlStmt = '''update rdb$procedures set rdb$description='%s'
                where rdb$procedure_name='%s' 
                ''' % (description, name.upper())
        elif category=='procedure_param':
            sqlStmt = '''update rdb$procedure_parameters 
                set rdb$description='%s'
                where rdb$procedure_name='%s' and rdb$parameter_name='%s'
                ''' % (description, name.upper(), name2.upper())
        elif category=='trigger':
            sqlStmt = '''update rdb$triggers set rdb$description='%s'
                where rdb$trigger_name='%s' 
                ''' % (description, name.upper())

        FbCommand(sqlStmt, self.conn).ExecuteNonQuery()

#------------------------------------------------------------------------------
if __name__ == '__main__':
    def on_execute_batch(sender, args):
        print 'on_execute_batch()'
        print args.CommandText
        print args.DataReader

    if len(sys.argv) == 2:
        testdir = sys.argv[1]
    else:
        testdir = System.IO.Path.GetTempPath()
        
    if testdir[-1] != '/':
        testdir += '/'
    print 'testdir=' + testdir

    conn_d = {
        'User' : 'SYSDBA',
        'Password' : 'masterkey',
        'DataSource' : 'localhost',
        'Database' : testdir + r'test.fdb',
        'Charset' : 'UNICODE_FSS', 
    }

    try:
        user_del(conn_d, 'Alice')
        user_del(conn_d, 'Bob')
        user_del(conn_d, 'Charlie')
        user_add(conn_d,'Alice','secret','Alice','Tester','A')
        user_add(conn_d,'Bob','secret','Bob','Tester','B')
        user_add(conn_d,'Charlie','secret','Charlie','Tester')
    except:
        print "Can't del & add user Alice, Bob and Chalie"

    conn_s = make_dict_to_string(conn_d, ignore_invalid_param=True)
    print conn_s
    print make_string_to_dict(conn_s)

    db = FbDatabase(conn_d,create_flag=True,forced_writes=True,over_write=True)
    db.open()

    db.execute_noq('CREATE ROLE role_a')
    db.execute_noq('CREATE ROLE role_b')

    # Create different connection
    # (execute_batch() connect and close automatically.)
    FbDatabase(conn_d).execute_batch("""
        CREATE DOMAIN dom_a
            AS INTEGER
            DEFAULT 9999
            CHECK (VALUE > 1000);

        CREATE DOMAIN dom_b
            AS VARCHAR(30)
            DEFAULT 'ABC'
            CHECK (VALUE <> 'ZZZ');

        CREATE EXCEPTION exception_a 'A test exception A';
        CREATE EXCEPTION exception_b 'A test exception B';


        CREATE TABLE foo (
            a INTEGER NOT NULL,
            b VARCHAR(30) NOT NULL UNIQUE,
            c VARCHAR(1024) NOT NULL,
            d DECIMAL(16,2) DEFAULT 0.0,
            e DATE,
            f TIMESTAMP,
            g BLOB SUB_TYPE 0, -- 0:binary 1:text
            PRIMARY KEY (a),
            CONSTRAINT CHECK_A CHECK (a <> 0)
        );

        CREATE TABLE bar (
            i INTEGER NOT NULL,
            j VARCHAR(30) NOT NULL,
            k VARCHAR(1024),
            PRIMARY KEY (i, j),
            FOREIGN KEY (j) REFERENCES foo(b) ON UPDATE CASCADE
        ); 

        CREATE TABLE baz (
            x INTEGER NOT NULL,
            y VARCHAR(30) NOT NULL,
            z VARCHAR(255),
            PRIMARY KEY (x, y),
            FOREIGN KEY (y) REFERENCES foo(b) ON UPDATE SET NULL
        ); 
        CREATE UNIQUE INDEX BAZ_INDEX ON BAZ(z);

        CREATE TABLE baz2 (
            x INTEGER NOT NULL,
            y VARCHAR(30) NOT NULL,
            z VARCHAR(255),
            PRIMARY KEY (x, y),
            FOREIGN KEY (y) REFERENCES foo(b) ON UPDATE SET DEFAULT
        ); 
        CREATE INDEX BAZ2_INDEX ON BAZ2(z);

        CREATE VIEW foo_view AS SELECT a,b,c,d,e FROM foo;
        CREATE VIEW foo_view2 AS SELECT a,b,c FROM foo;

        CREATE GENERATOR gen_foo;
        SET GENERATOR gen_foo to 1000;
        set term !! ;

        CREATE TRIGGER set_foo_primary FOR foo
          BEFORE INSERT
          AS BEGIN
            new.a = gen_id(gen_foo,1);
          END 
        !!
        CREATE TRIGGER set_foo_inact FOR foo
          BEFORE INSERT
          AS BEGIN
            new.a = gen_id(gen_foo,1);
          END
        !!
        ALTER TRIGGER set_foo_inact INACTIVE
        !!
        CREATE TRIGGER database_trigger_connect_act ON CONNECT
          AS BEGIN
            -- nothing
          END
        !!
        CREATE TRIGGER database_trigger_connect_inact INACTIVE ON CONNECT
          AS BEGIN
            -- nothing
          END
        !!
        CREATE TRIGGER database_trigger_disconnect ON DISCONNECT
          AS BEGIN
            -- nothing
          END
        !!
        CREATE TRIGGER database_trigger_tran_start ON TRANSACTION START
          AS BEGIN
            -- nothing
          END
        !!
        CREATE TRIGGER database_trigger_tran_commit ON TRANSACTION COMMIT
          AS BEGIN
            -- nothing
          END
        !!
        CREATE TRIGGER database_trigger_tran_rollback ON TRANSACTION ROLLBACK
          AS BEGIN
            -- nothing
          END
        !!
        CREATE PROCEDURE FOO_PROC (param_b VARCHAR(30))
          RETURNS (sum_a INTEGER, avg_a DECIMAL(12, 2))
          AS
          BEGIN
            SELECT SUM(a), AVG(A)
              FROM FOO
              WHERE b = :param_b
              INTO :sum_a, :avg_a;
            EXIT;
          END 
        !!
        set term ; !! 

        CREATE SEQUENCE seq_foo;

        GRANT ROLE_A To Alice, Bob;
        GRANT SELECT, UPDATE on FOO to ROLE_A;
        GRANT INSERT, REFERENCES(C), UPDATE(C,D) on FOO to Bob;
    """, on_execute_batch)

    FbDatabase(conn_d).execute_batch("""
        DROP VIEW foo_view2
    """, on_execute_batch)

    # Declare external function
    try:
        udfSQL = Env.GetFolderPath(Env.SpecialFolder.ProgramFiles)
        udfSQL += r'\Firebird\Firebird_2_1\UDF\fbudf.sql'
        f = open(udfSQL, 'r')
        while (f.readline()[:2] != '--'):
            pass    # skip
        FbDatabase(conn_d).execute_batch(f.read(), on_execute_batch)
        f.close()
    except Exception, e:
        print "Can't load UDF functions."

    db.write_description('domain', "Domain A's description", 'dom_a')
    db.write_description('role', "Role A's description", 'role_a')
    db.write_description('table', "Table FOO's description", 'foo')
    db.write_description('table', "VIEW FOO_VIEW's description", 'foo_view')
    db.write_description('column', "Table FOO's A description", 'foo', 'a')
    db.write_description('column', "View FOO_VIEW's A ", 'foo_view', 'a')
    db.write_description('exception', "Test Exception", 'exception_a')
    db.write_description('procedure', "Test Procedure", 'foo_proc')
    db.write_description('procedure_param', "In param", 'foo_proc', 'param_b')
    db.write_description('procedure_param', "Out param 1", 'foo_proc', 'sum_a')
    db.write_description('procedure_param', "Out param 2", 'foo_proc', 'avg_a')
    db.write_description('trigger', "Trigger's description", 'set_foo_primary')

    db.close()

    server_log(conn_d)

    user_add(conn_d, 'WWWXXXYYYZZZ', 'secret')
    user_del(conn_d, 'WWWXXXYYYZZZ')

    user_mod(conn_d, 'Charlie', 'SECRET', 'Charlie', 'X', 'Y')

    print "\n[users]"
    for u in users_list(conn_d):
        print u['NAME'], u['FIRST'], u['MIDDLE'], u['LAST']

    print "\n[backup bar]"
    db_backup(conn_d, testdir + r'bar.fbk', oh=_print_handler)
    conn_d['Database'] = testdir + r'bar.fdb'
    db_restore(conn_d, testdir + r'bar.fbk', oh=_print_handler)

    print "\n[connect bar]"
    try:
        db = FbDatabase(conn_d)
        db.open()
    except Exception, e:
        print str(e)
        sys.exit()

    print "[info]"
    print db.info()

    print "\n[domains]"
    for d in db.domains():
        print d['NAME'],
        print d['VALIDATION_SOURCE'],   # check constraint
        print d['DEFAULT_SOURCE']       # default value
        print d['DESCRIPTION']
        print db.domains(d['NAME'])

    print "\n[exceptions]"
    for e in db.exceptions():
        print e['NAME'] + ' ' + e['MESSAGE_STRING'], e['DESCRIPTION']

    print "\n[system tables]"
    for t in db.tables(system_flag=1):
        print t['NAME'], t['OWNER'], t['DESCRIPTION']

    print "\n[tables]"
    for t in db.tables():
        print '\n'+t['NAME'], t['OWNER']
        for c in db.columns(t['NAME']):
            print '\t' + c['NAME'] + ' ' + fieldtype_to_string(c),
            print c['DESCRIPTION']
        print '\t[key_constraints_and_index:]\n',
        for kcs in db.key_constraints_and_index(t['NAME']):
            for k in kcs:
                print '\t'+k, kcs[k]
            print '\n'
                
        print '\t[check_constraints:]\n',
        for ccs in db.check_constraints(t['NAME']):
            for k in ccs:
                print '\t'+k, ccs[k]
            print '\n'

        print '\t[constraints:]\n',
        for cs in db.constraints(t['NAME']):
            print cs

        print '\t[primary_keys:]\n',
        for pk in db.primary_keys(t['NAME']):
            print pk

        print '\t[foreign_keys:]\n',
        for fk in db.foreign_keys(t['NAME']):
            print fk

        print '\t[unique_keys:]\n',
        for uk in db.unique_keys(t['NAME']):
            print uk

        print '\n  triggers:',
        for c in db.triggers(t['NAME']):
            print c['NAME'], c['SEQUENCE'],c['TRIGGER_TYPE'], c['INACT']
            print db.trigger_source(c['NAME'])['SOURCE']

    print "\n[views]"
    for t in db.views():
        print t['NAME'], t['OWNER']
        for c in db.columns(t['NAME']):
            print '\t' + c['NAME'] + ' ' + fieldtype_to_string(c),
            print c['DESCRIPTION']
        print db.view_source(t['NAME'])

    print "\n[generators]"
    for g in db.generators():
        print g['NAME'], g['COUNT'], 
        print db.get_generator_id(g['NAME'])

    print "\n[procedure]"
    for p in db.procedures():
        print p['NAME']
        q = db.procedure_source(p['NAME'].strip())
        print q['SOURCE']
        print "\n[in_params]"
        for inp in q['IN_PARAMS']:
            print inp['NAME'], fieldtype_to_string(inp)
        print "\n[out_params]"
        for outp in q['OUT_PARAMS']:
            print outp['NAME'], fieldtype_to_string(outp)

    print "\n[roles]"
    for r in db.roles():
        print r['NAME'] + ' ' + r['OWNER']
        print "\t[grant_users]"
        for u in db.grant_users(r['NAME'].strip()):
            print '\t', u['NAME'], u['PRIVILEGE'], u['GRANT_OPTION'],
            if IsDBNull(u['FIELD_NAME']):
                print u['FIELD_NAME']
            else:
                print 

    print "\n[functions]"
    for f in db.function_names():
        print f['FUNCTION_NAME']

    print "\n[set not null flag]"
    print db.set_not_null('foo', 'c', False)
    print db.set_not_null('foo', 'd', True)
    db.execute_noq('''insert into foo (a,b,d) values (1, 'ABC', 1.1)''')
    db.execute_noq('''insert into foo (a,b,d) values (1, 'DEF', 2.1)''')
    for c in db.execute('''select * from foo'''):
        for i in range(c.FieldCount):
            print c[i]
    print db.set_not_null('foo', 'c', True)
    db.execute_noq('''update foo set c = 'Not NULL value' ''')
    print db.set_not_null('foo', 'c', True)
    print db.set_not_null('foo', 'a', False)

    print "\n[reorder column]"
    db.reorder_fields('foo', ['g', 'f', 'e', 'd', 'c', 'b', 'a'])
    for t in db.tables():
        print t['NAME']
        for c in db.columns(t['NAME']):
            print '\t' + c['NAME'], fieldtype_to_string(c)
        print '\n<primary keys>'
        for c in db.primary_keys(t['NAME']):
            print c

    print "\n[copy table]\n",
    for t in db.tables():
        print t['NAME']
    db.copy_table('foo', 'foo_copied')
    db.copy_table('foo_copied', 'foo_copied2')
    db.copy_table('baz2', 'baz2_copied')
    print "-->\n",
    for t in db.tables():
        print t['NAME']
        for k in db.foreign_keys(t['NAME'].strip()):
            print ",".join(['PK=' + k['FIELD_NAME'].strip(), 
                k['REF_TABLE'].strip(), k['REF_FIELD'].strip(), 
                k['UPDATE_RULE'], k['DELETE_RULE']])
        for r in db.referenced_columns(t['NAME'].strip()):
            print "column %s referenced from %s %s(%s)" % (
                r['FIELD_NAME'].strip(), r['CONST_NAME'].strip(), 
                r['REFERENCED_TABLE'].strip(), r['REFERENCED_FIELD'].strip())

    db.close()

    print "\n[backup metadata to baz.fbk]"
    # Backup MetaData only
    db_backup(conn_d, testdir + r'baz.fbk', meta_only=True)
    conn_d['Database'] = testdir + r'baz.fdb'
    db_restore(conn_d, testdir + r'baz.fbk')


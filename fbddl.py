##############################################################################
# Copyright (c) 2007,2015, Hajime Nakagami<nakagami@gmail.com>
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
import sys
import clr
clr.AddReference("System.Data")
import System.IO
from System.Convert import IsDBNull

import fbutil


def fb_builtintype_to_string(d):
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

    return s


def fb_fieldtype_to_string(d):
    if d['FIELD_NAME'][:4] != 'RDB$':
        s = d['FIELD_NAME'].strip()     # DOMAIN's name
    else:   # Builtin type
        s = fb_builtintype_to_string(d)

    if not IsDBNull(d['DEFAULT_SOURCE']):
        s += ' ' + d['DEFAULT_SOURCE']

    if d['NULL_FLAG'] == 1:
        s += ' NOT NULL'

    return s


def get_ddl(conn_d, debug=False):
    sql_stmt = ''
    fb_db = fbutil.FbDatabase(conn_d)
    fb_db.open()

    # Domains
    for d in fb_db.domains():
        sql_stmt += 'create domain "' + d['NAME'].strip() + '"'
        sql_stmt += ' as ' + fb_builtintype_to_string(d)
        if not IsDBNull(d['DEFAULT_SOURCE']):
            sql_stmt += ' ' + d['DEFAULT_SOURCE']
        if not IsDBNull(d['VALIDATION_SOURCE']):
            sql_stmt += ' ' + d['VALIDATION_SOURCE']
        sql_stmt += ';\n'
    sql_stmt += '\n'

    # Tables
    for t in fb_db.tables():
        tab_name = t['NAME'].strip()
        pks = fb_db.primary_keys(tab_name)
        uks = fb_db.unique_keys(tab_name)
        sql_stmt += 'create table "' + tab_name + '"(\n'
        col_str = []
        for c in fb_db.columns(tab_name):
            s = '    "' + c['NAME'].strip() + '" '
            s += fb_fieldtype_to_string(c)
            if c['NAME'].strip() in uks:
                s += ' UNIQUE'
            col_str.append(s)
        sql_stmt += ",\n".join(col_str)
        if len(pks):
            sql_stmt += ',\n    PRIMARY KEY ("' + '","'.join(pks) + '")'
        sql_stmt += ");\n"
    sql_stmt += '\n'

    # Views
    for v in fb_db.views():
        sql_stmt += 'create view "%s" as %s;' % (
            v['NAME'].strip(), fb_db.view_source(v['NAME'].strip()))
    sql_stmt += '\n'

    # Generators
    for g in fb_db.generators():
        sql_stmt += 'create generator "%s";\nset generator "%s" to %d;\n' % (
            g['NAME'], g['NAME'], g['COUNT'])
    sql_stmt += '\n'

    if fb_db.execute_sca('select count(*) from rdb$procedures') \
            or fb_db.execute_sca('''select count(*) from rdb$triggers
                    where (rdb$system_flag is null or rdb$system_flag = 0)'''):
        sql_stmt += 'set term !! ;\n'
        # Procedures
        for p in fb_db.procedures():
            proc = fb_db.procedure_source(p['Name'].strip())
            sql_stmt += 'create procedure ' + proc['NAME'] + '('
            sql_stmt += ','.join([in_p['NAME'] + ' ' + fb_fieldtype_to_string(in_p) for in_p in proc['IN_PARAMS']])
            sql_stmt += ')\nreturns ('
            sql_stmt += ','.join([out_p['NAME'] + ' ' + fb_fieldtype_to_string(out_p) for out_p in proc['OUT_PARAMS']])
            sql_stmt += ') as\n' + '\n'.join(proc['SOURCE'].split('\n'))
            sql_stmt += '\n'
        sql_stmt += '\n'

        # Triggers
        t_type = {
            1: 'before insert ',
            2: 'after insert ',
            3: 'before update ',
            4: 'after update ',
            5: 'before delete ',
            6: 'after delete ',
            8192: 'on connect',
            8193: 'on disconnect ',
            8194: 'on transaction start ',
            8195: 'on transaction commit ',
            8196: 'on transaction rollback ',
        }
        for t in fb_db.triggers():
            r = fb_db.trigger_source(t['NAME'].strip())
            sql_stmt += 'create trigger "' + t['NAME'].strip() + '"\n'
            if r['INACT']:
                sql_stmt += 'inactive \n'
            else:
                sql_stmt += 'active \n'
            if not IsDBNull(r['TABLE_NAME']):
                sql_stmt += ' on "' + r['TABLE_NAME'].strip() + '"\n'
            sql_stmt += t_type[int(r['TRIGGER_TYPE'])]
            sql_stmt += ' position ' + str(r['SEQUENCE']) + '\n'
            sql_stmt += '\n'.join(r['SOURCE'].split('\n'))
            sql_stmt += '\n'

        sql_stmt += '!!\nset term ; !!'
        sql_stmt += '\n'

    # Foreign key
    for t in fb_db.tables():
        for fk in fb_db.foreign_keys(tab_name):
            sql_stmt += 'alter table "%s" add foreign key("%s") references "%s"("%s");\n' % (
                t['NAME'].strip(), fk['FIELD_NAME'].strip(),
                fk['REF_TABLE'].strip(), fk['REF_FIELD'].strip()
            )
    sql_stmt += '\n'

    # Check constraints
    for t in fb_db.tables():
        tab_name = t['NAME'].strip()
        for chk in fb_db.check_constraints(tab_name):
            sql_stmt += 'alter table "%s" add constraint "%s" %s;\n' % (
                tab_name, chk['CHECK_NAME'], chk['CHECK_SOURCE'])
    sql_stmt += '\n'

    fb_db.close()
    return sql_stmt


if __name__ == '__main__':
    if len(sys.argv) == 2:
        testdir = sys.argv[1]
        if testdir[-1] != '\\':
            testdir = testdir + '\\'
    else:
        testdir = System.IO.Path.GetTempPath()

    print 'testdir=' + testdir

    targets = ['foo', 'bar', 'baz']
    for db_name in targets:
        conn_d = {
            'User': 'SYSDBA',
            'Password': 'masterkey',
            'DataSource': 'localhost',
            'Database': testdir + db_name + '.fdb',
            'Charset': 'UNICODE_FSS',
        }

        print get_ddl(conn_d)

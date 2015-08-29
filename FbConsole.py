##############################################################################
# Copyright (c) 2007-2009,2015, Hajime Nakagami<nakagami@gmail.com>
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
import clr
import sys
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
clr.AddReference("System.Data")
from System.Windows import Forms
from System.Drawing import Size, Image, Color
from System.Data import DataTable
from System.IO import UserPasswordForm
from System.Convert import IsDBNull
from System.Type import GetType
import System.Threading.Mutex
import FbSqlForm
import formutil
import dialogform
import fbutil
import fbddl


def is_Mono():
    if GetType("Mono.Runtime"):
        return True
    else:
        return False


APP_NAME = 'FbConsole'
__version__ = '0.10.0'
img_files = [
    'root', 'server', 'database', 'domain', 'object', 'function',
    'generators', 'generator', 'procedures', 'procedure',
    'systemtables', 'systemtable', 'tables', 'table',
    'trigger', 'trigger_inact', 'view', 'search', 'key', 'column',
]


DBTREE_FILE = 'FbConsoleDB.cfg'
USER_PROFILE = 'FbConsoleUserProf.cfg'

UP_BUTTON_COLUMN_INDEX = 2
DOWN_BUTTON_COLUMN_INDEX = 3
NOT_NULL_CHECK_COLUMN_INDEX = 4

MOD_USER_BUTTON_COLUMN_INDEX = 4

PK_COLOR = Color.Yellow
FK_COLOR = Color.Green
PK_FK_COLOR = Color.YellowGreen
UK_COLOR = Color.LightGray

INPUT_COLOR = Color.LightYellow
NEW_DATA_COLOR = Color.LightBlue


def eventhook(fn):
    return fn   # NDEBUG

    def f(*args):
        print fn, args
        return fn(*args)
    return f


def sqlquote(s):
    if type(s) == str:
        return s.replace("'", "''")


class BackupRestoreForm(Forms.Form):
    def __init__(self, conn_d, filename, is_backup):
        self.Width = 450
        self.Height = 100
        self.is_backup = is_backup
        if self.is_backup:
            self.Text = 'Backup '
        else:
            self.Text = 'Restore '

        self.Text = self.Text + conn_d['DataSource'] + ':' + conn_d['Database']
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self.conn_d = conn_d

        self.Controls.Add(
            Forms.Label(Left=3, Top=13, Text="Backup File:", AutoSize=True))
        self._filePath = Forms.TextBox(Left=70, Top=10, Width=310)
        self._filePath.Text = filename
        self._filePath.TabIndex = 1
        self.Controls.Add(self._filePath)
        self._pathButton = Forms.Button(
            Text="...", Left=406, Top=10, Size=Size(24, 24))
        self._pathButton.Click += self.OnBakcupFileOpen
        self._pathButton.TabIndex = 2
        self.Controls.Add(self._pathButton)
        if self.is_backup:
            self._metaonly = Forms.CheckBox(
                Left=50, Top=35, Text="Metadata Only", AutoSize=True)
            self.Controls.Add(self._metaonly)
        else:
            self._overwrite = Forms.CheckBox(
                Left=50, Top=35, Text="Overwrite", AutoSize=True)
            self.Controls.Add(self._overwrite)

        self.AcceptButton = Forms.Button(Left=267, Top=40, Size=Size(75, 23))
        if self.is_backup:
            self.AcceptButton.Text = "&Backup"
        else:
            self.AcceptButton.Text = "&Restore"
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 3
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(
            Text="&Close", Left=348, Top=40, Size=Size(75, 23))
        self.CancelButton.TabIndex = 4
        self.Controls.Add(self.CancelButton)

        self._result = Forms.TextBox(Left=20, Top=85, Width=400, Height=210)
        self._result.Multiline = True
        self._result.ReadOnly = True
        self._result.ScrollBars = Forms.ScrollBars.Vertical
        self.Controls.Add(self._result)

    def OnBakcupFileOpen(self, sender, args):
        ofd = Forms.OpenFileDialog()
        ofd.CheckFileExists = False
        r = ofd.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._filePath.Text = ofd.FileName

    def OnOk(self, sender, args):
        self.Height = 340
        self._result.Text = ''

        if self.conn_d['Password'] is None:
            dialog = UserPasswordForm(self.conn_d)
            r = dialog.ShowDialog(self)
            if r != Forms.DialogResult.OK:
                return
        try:
            if self.is_backup:
                fbutil.db_backup(
                    self.conn_d, self._filePath.Text, self._metaonly.Checked, self.log)
            else:
                fbutil.db_restore(self.conn_d, self._filePath.Text, self._overwrite.Checked, self.log)
        except Exception, e:
            if self.is_backup:
                Forms.MessageBox.Show(str(e), "Can't backup database")
            else:
                Forms.MessageBox.Show(str(e), "Can't restore database")
            if self.conn_d.get('PrevUser'):
                self.conn_d['User'] = self.conn_d['PrevUser']
                del self.conn_d['PrevUser']
                self.conn_d['Password'] = self.conn_d['PrevPassword']
                del self.conn_d['PrevPassword']

    def log(self, o, e):
        self._result.Text = self._result.Text + e.Message + '\r\n'


class MainForm(Forms.Form):
    def imgidx(self, name):
        return img_files.index(name)

    def node_to_mssql_conndict(self, node, is_import):
        d = {}
        d['MSSQL_Server'] = self.user_pref.get('MSSQL_Server')
        if is_import:
            d['MSSQL_Database'] = self.user_pref.get('MSSQL_ImportDatabase')
        else:
            d['MSSQL_Database'] = self.user_pref.get('MSSQL_ExportDatabase')
        d['MSSQL_User'] = self.user_pref.get('MSSQL_User')
        d['MSSQL_Password'] = self.user_pref.get('MSSQL_Password')
        d['MSSQL_SAVE_PASS_FLAG'] = self.user_pref.get('MSSQL_SAVE_PASS_FLAG')

        while node.Parent:
            t = node.Tag
            if t['NODE_TYPE'] == 'SERVER':
                d['DataSource'] = t['SERVER']
            if t['NODE_TYPE'] == 'DATABASE':
                d.update(t)
            node = node.Parent
        return d

    def node_to_oracle_conndict(self, node, is_import):
        d = {}
        d['ORACLE_Server'] = self.user_pref.get('ORACLE_Server')
        d['ORACLE_User'] = self.user_pref.get('ORACLE_User')
        d['ORACLE_Password'] = self.user_pref.get('ORACLE_Password')
        d['ORACLE_SAVE_PASS_FLAG'] = \
                self.user_pref.get('ORACLE_SAVE_PASS_FLAG', '0')

        while node.Parent:
            t = node.Tag
            if t['NODE_TYPE'] == 'SERVER':
                d['DataSource'] = t['SERVER']
            if t['NODE_TYPE'] == 'DATABASE':
                d.update(t)
            node = node.Parent
        return d

    def node_to_sqlite_conndict(self, node, is_import):
        d = {}
        d['SQLite_Path'] = self.user_pref.get('SQLite_Path')

        while node.Parent:
            t = node.Tag
            if t['NODE_TYPE'] == 'SERVER':
                d['DataSource'] = t['SERVER']
            if t['NODE_TYPE'] == 'DATABASE':
                d.update(t)
            node = node.Parent
        return d

    def node_to_conndict(self, node):
        t = node.Tag
        if t['NODE_TYPE'] != 'SERVER' and t['NODE_TYPE'] != 'DATABASE':
            return None
        if t['NODE_TYPE'] == 'DATABASE':
            d = {'DataSource' : node.Parent.Tag['SERVER']}
        else:   # SERVER
            d = {'DataSource' : t['SERVER']}

        for k in ('Database', 'User', 'Password', 'Role', 'Port'):
            d[k] = t.get(k)
        d['Charset'] = t.get('Charset', 'UNICODE_FSS')
        d['SAVE_PASS_FLAG'] = t.get('SAVE_PASS_FLAG', '0')

        return d

    def conn_from_node(self, node):
        while (node and node.Tag.get('NODE_TYPE') != 'DATABASE'):
            node = node.Parent
        if node:
            return node.Tag['CONNECTION']
        return None

    def save_tree(self):
        pref = {}

        # TreeView
        d = {}
        for server_node in self._tv.Nodes[0].Nodes:
            sv_dict = {'SERVER': server_node.Tag['SERVER']}
            sv_dict['User'] = server_node.Tag.get('User','')
            if int(server_node.Tag.get('SAVE_PASS_FLAG', '0')):
                sv_dict['Password'] = server_node.Tag.get('Password', '')

            d[server_node.Text] = [fbutil.make_dict_to_string(
                                    sv_dict, ignore_invalid_param = False)]
            for db_node in server_node.Nodes:
                db_dict = {}
                for k in ('DISPLAY_NAME', 'SAVE_PASS_FLAG', 'Database', 
                        'User', 'Charset', 'Role', 'Port', 'BACKUP_FILENAME'):
                    if k in db_node.Tag:
                        db_dict[k] = db_node.Tag[k]
                if int(db_dict.get('SAVE_PASS_FLAG')):
                    db_dict['Password'] = db_node.Tag['Password']
                d[server_node.Text].append(fbutil.make_dict_to_string(
                                db_dict, '\n', ignore_invalid_param = False))
        formutil.userpref_save(d, DBTREE_FILE)
    
    def load_tree(self):
        try:
            pref = formutil.userpref_load(DBTREE_FILE)
        except:
            pref = {}

        # TreeView
        self._tv.Nodes.Clear()
        self._tv.Nodes.Add(APP_NAME)
        self._tv.Nodes[0].ContextMenuStrip = self._cmenu_top
        self._tv.Nodes[0].Tag = {'NODE_TYPE': 'TOP'}
        d = pref
        if d:
            for k in d.keys():
                img = self.imgidx('server')
                server_node = Forms.TreeNode(k, img, img)
                server_node.ContextMenuStrip = self._cmenu_server
                server_node.Tag = {'NODE_TYPE': 'SERVER'}
                sv_dict = fbutil.make_string_to_dict(d[k][0])
                if sv_dict.get('Password'):
                    sv_dict['SAVE_PASS_FLAG'] = '1'
                server_node.Tag.update(sv_dict)

                for db_string in d[k][1:]:
                    img = self.imgidx('database')
                    db_dict = fbutil.make_string_to_dict(db_string, '\n')
                    db_node = Forms.TreeNode(db_dict['DISPLAY_NAME'], img, img)
                    db_node.ContextMenuStrip = self._cmenu_db
                    db_node.Tag={'NODE_TYPE': 'DATABASE', 'CONNECTION': None}
                    db_node.Tag.update(db_dict)
                    server_node.Nodes.Add(db_node)
                self._tv.Nodes[0].Nodes.Add(server_node)

    def active_triggers(self, conn):
        r = []
        for t in conn.triggers():
            if not t['INACT']:
                r.append(t['NAME'].strip())
        return r

    def select_node(self, sender, args, node_type=None):
        node = self._tv.SelectedNode
        if node_type:
            while node:
                if node.Tag['NODE_TYPE'] == node_type:
                    break
                node = node.Parent
        elif node:
            if type(node.Tag) != type({}) or not 'NODE_TYPE' in node.Tag:
                node = None

        if node:
            self.Text = node.FullPath
        return node

    def ConfirmSql(self, conn, sql):
        if self.menu['CONFIRM_SQL'].Checked:
            dialog = dialogform.SimpleSqlForm(conn, sql, read_only = True)
            if dialog.ShowDialog(self) == Forms.DialogResult.OK:
                return True
            else:
                return False
        try:
            conn.execute_noq(sql)
            return True
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Error")
            return False

    def ChangeMenuEnabled(self, node):
        if node.Tag['NODE_TYPE'] == 'TOP':
            self.menu['REG_SERVER'].Enabled = True
        else:
            self.menu['REG_SERVER'].Enabled = False

        if node.Tag['NODE_TYPE'] == 'SERVER':
            self.menu['REG_DB'].Enabled = True
            self.menu['UNREG_SERVER'].Enabled = True
            self.menu['CREATE_DB'].Enabled = True
            self.menu['EDIT_SERVER'].Enabled = True
        else:
            self.menu['REG_DB'].Enabled = False
            self.menu['UNREG_SERVER'].Enabled = False
            self.menu['CREATE_DB'].Enabled = False
            self.menu['EDIT_SERVER'].Enabled = False

        if node.Tag['NODE_TYPE'] == 'DATABASE':
            self.menu['UNREG_DB'].Enabled = True
            self.menu['EDIT_DB'].Enabled = True
            if node.Tag['CONNECTION']:
                self.menu['OPEN_DB'].Enabled = False
                self.menu['CLOSE_DB'].Enabled = True
            else:
                self.menu['OPEN_DB'].Enabled = True
                self.menu['CLOSE_DB'].Enabled = False
        else:
            self.menu['UNREG_DB'].Enabled = False
            self.menu['EDIT_DB'].Enabled = False
            self.menu['OPEN_DB'].Enabled = False
            self.menu['CLOSE_DB'].Enabled = False

        while node.Tag['NODE_TYPE'] != 'DATABASE' and node.Parent:
            node = node.Parent
        if node.Tag['NODE_TYPE'] == 'DATABASE':
            self.menu['ISQL'].Enabled = True
            self.menu['EXPORT_DDL'].Enabled = True
            self.menu['BACKUP_DB'].Enabled = True
        else:
            self.menu['ISQL'].Enabled = False
            self.menu['EXPORT_DDL'].Enabled = False
            self.menu['BACKUP_DB'].Enabled = False

        if node and node.Tag.get('CONNECTION'):
            self.menu['REFRESH_TREE'].Enabled = True
            self.cmenu_db['REFRESH_TREE'].Enabled = True
            self.menu['RESTORE_DB'].Enabled = False
            self.cmenu_db['RESTORE_DB'].Enabled = False
        else:
            self.menu['REFRESH_TREE'].Enabled = False
            self.cmenu_db['REFRESH_TREE'].Enabled = False
            self.menu['RESTORE_DB'].Enabled = True
            self.cmenu_db['RESTORE_DB'].Enabled = True

    def WalkAndUpdateTriggerNode(self, node, active_triggers):
        img_ti = self.imgidx('trigger_inact')
        img_ta = self.imgidx('trigger')
        for n in node.Nodes:
            self.WalkAndUpdateTriggerNode(n, active_triggers)
        if node.Tag['NODE_TYPE'] == 'TRIGGER':
            if node.Text in active_triggers:
                node.ImageIndex = img_ta
                node.SelectedImageIndex = img_ta
            else:
                node.ImageIndex = img_ti
                node.SelectedImageIndex = img_ti

    def WalkAndRemoveTriggerNode(self, node, trigger_name):
        for n in node.Nodes:
            self.WalkAndRemoveTriggerNode(n, trigger_name)
        if node.Tag['NODE_TYPE'] == 'TRIGGER' and node.Name == trigger_name:
            node.Parent.Nodes.Remove(node)

    def PopulateDomains(self, node):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()
        img = self.imgidx('domain')
        for dm in self.conn_from_node(node).domains():
            n = Forms.TreeNode(
                dm['NAME'].strip()+' '+fbutil.fieldtype_to_string(dm, False), 
                img, img)
            n.Name = dm['NAME'].strip()
            n.ContextMenuStrip = self._cmenu_domain
            n.Tag = {'NODE_TYPE': 'DOMAIN'}
            node.Nodes.Add(n)

    def PopulateGenerators(self, node):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()
        img = self.imgidx('generator')
        for g in conn.generators():
            n = Forms.TreeNode(g['NAME'].strip(), img, img)
            n.Name = g['NAME'].strip()
            n.ContextMenuStrip = self._cmenu_generator
            n.Tag = {'NODE_TYPE': 'GENERATOR'}
            node.Nodes.Add(n)

    def PopulateProcedures(self, node):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()
        img = self.imgidx('procedure')
        for pc in self.conn_from_node(node).procedures():
            n = Forms.TreeNode(pc['NAME'].strip(), img, img)
            n.Name = pc['NAME'].strip()
            n.ContextMenuStrip = self._cmenu_procedure
            n.Tag = {'NODE_TYPE': 'PROCEDURE'}
            node.Nodes.Add(n)

    def PopulateRoles(self, node):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()
        img = self.imgidx('object')
        for r in self.conn_from_node(node).roles():
            n = Forms.TreeNode(r['NAME'].strip(), img, img)
            n.Name = r['NAME'].strip()
            n.ContextMenuStrip = self._cmenu_role
            n.Tag = {'NODE_TYPE': 'ROLE'}
            node.Nodes.Add(n)

    def PopulateDB(self, server_node, conn_d):
        conn_d['NODE_TYPE'] = 'DATABASE'
        img = self.imgidx('database')
        n = Forms.TreeNode(conn_d['DISPLAY_NAME'], img, img)
        n.ContextMenuStrip = self._cmenu_db
        n.Tag = conn_d
        if not 'CONNECTION' in n.Tag:
            n.Tag['CONNECTION'] = None
        self._tv.BeginUpdate()
        server_node.Nodes.Add(n)
        self._tv.EndUpdate()
        return n

    def PopulateTables(self, node, system_flag = 0):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()
        if system_flag:
            img = self.imgidx('systemtable')
        else:
            img = self.imgidx('table')
        for tb in conn.tables(system_flag):
            n = Forms.TreeNode(tb['NAME'].strip(), img, img)
            n.Name = tb['NAME'].strip()
            if system_flag:
                n.ContextMenuStrip = self._cmenu_systemtable
                n.Tag = {'NODE_TYPE': 'SYSTEMTABLE'}
            else:
                n.ContextMenuStrip = self._cmenu_table
                n.Tag = {'NODE_TYPE': 'TABLE'}
            node.Nodes.Add(n)

    def PopulateTable(self, node):
        conn = self.conn_from_node(node)
        tab_name = node.Name
        node.Nodes.Clear()

        img_key = self.imgidx('key')
        img_col = self.imgidx('column')
        pks = conn.primary_keys(tab_name)
        for c in conn.columns(tab_name):
            cn = c['NAME'].strip()
            s = cn + ' ' + fbutil.fieldtype_to_string(c)

            if cn in pks:
                n = Forms.TreeNode(s, img_key, img_key)
            else:
                n = Forms.TreeNode(s, img_col, img_col)
            n.Name = cn
            n.ContextMenuStrip = self._cmenu_columns
            n.Tag = {'NODE_TYPE': 'COLUMN'}
            node.Nodes.Add(n)

        img_ti = self.imgidx('trigger_inact')
        img_ta = self.imgidx('trigger')
        for tg in conn.triggers(tab_name):
            if tg['INACT']:
                n = Forms.TreeNode(tg['NAME'].strip(), img_ti, img_ti)
            else:
                n = Forms.TreeNode(tg['NAME'].strip(), img_ta, img_ta)
            n.ContextMenuStrip = self._cmenu_trigger
            n.Name = tg['NAME'].strip()
            n.Tag = {'NODE_TYPE': 'TRIGGER'}
            node.Nodes.Add(n)

    def PopulateTriggers(self, node):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()

        img_ti = self.imgidx('trigger_inact')
        img_ta = self.imgidx('trigger')
        for tg in conn.triggers():
            if tg['INACT']:
                img = img_ti
            else:
                img = img_ta
            n = Forms.TreeNode(tg['NAME'].strip(), img, img)
            n.Name = tg['NAME'].strip()
            n.ContextMenuStrip = self._cmenu_trigger
            n.Tag = {'NODE_TYPE': 'TRIGGER'}
            node.Nodes.Add(n)

    def PopulateViews(self, node):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()

        img = self.imgidx('view')
        for vw in conn.views():
            n = Forms.TreeNode(vw['NAME'].strip(), img, img)
            n.Name = vw['NAME'].strip()
            n.ContextMenuStrip = self._cmenu_view
            n.Tag = {'NODE_TYPE': 'VIEW'}
            node.Nodes.Add(n)

    def PopulateDBItems(self, node):
        conn = self.conn_from_node(node)
        node.Nodes.Clear()

        img = self.imgidx('search')
        n = Forms.TreeNode('Info', img, img)
        n.Tag = {'NODE_TYPE': 'INFO'}
        node.Nodes.Add(n)

        img = self.imgidx('domain')
        n = Forms.TreeNode('Domains', img, img)
        n.Tag = {'NODE_TYPE': 'DOMAINS'}
        n.ContextMenuStrip = self._cmenu_domains
        node.Nodes.Add(n)
        self.PopulateDomains(n)

        img = self.imgidx('object')
        n = Forms.TreeNode('Exceptions', img, img)
        n.ContextMenuStrip = self._cmenu_exceptions
        n.Tag = {'NODE_TYPE': 'EXCEPTIONS'}
        node.Nodes.Add(n)

        img = self.imgidx('function')
        n = Forms.TreeNode('Functions', img, img)
        n.Tag = {'NODE_TYPE': 'FUNCTIONS'}
        n.ContextMenuStrip = self._cmenu_functions
        node.Nodes.Add(n)

        img = self.imgidx('generators')
        n = Forms.TreeNode('Generators', img, img)
        n.Tag = {'NODE_TYPE': 'GENERATORS'}
        n.ContextMenuStrip = self._cmenu_generators
        node.Nodes.Add(n)
        self.PopulateGenerators(n)

        img = self.imgidx('procedures')
        n = Forms.TreeNode('Procedures', img, img)
        n.Tag = {'NODE_TYPE': 'PROCEDURES'}
        n.ContextMenuStrip = self._cmenu_procedures
        node.Nodes.Add(n)
        self.PopulateProcedures(n)

        img = self.imgidx('object')
        n = Forms.TreeNode('Roles', img, img)
        n.ContextMenuStrip = self._cmenu_roles
        n.Tag = {'NODE_TYPE': 'ROLES'}
        node.Nodes.Add(n)
        self.PopulateRoles(n)

        img = self.imgidx('systemtables')
        n = Forms.TreeNode('System Tables', img, img)
        n.Tag = {'NODE_TYPE': 'SYSTEMTABLES'}
        node.Nodes.Add(n)
        self.PopulateTables(n, system_flag = 1)

        img = self.imgidx('tables')
        n = Forms.TreeNode('Tables', img, img)
        n.ContextMenuStrip = self._cmenu_tables
        n.Tag = {'NODE_TYPE': 'TABLES'}
        node.Nodes.Add(n)
        self.PopulateTables(n)

        img = self.imgidx('trigger')
        n = Forms.TreeNode('Triggers', img, img)
        n.Tag = {'NODE_TYPE': 'TRIGGERS'}
        node.Nodes.Add(n)
        self.PopulateTriggers(n)

        img = self.imgidx('view')
        n = Forms.TreeNode('Views', img, img)
        n.ContextMenuStrip = self._cmenu_views
        n.Tag = {'NODE_TYPE': 'VIEWS'}
        node.Nodes.Add(n)
        self.PopulateViews(n)

    def ConnectDB(self, node):
        if node.Tag['CONNECTION']:  # Already connected
            return
        d = self.node_to_conndict(node)
        if not d:
            return
        if d['Password'] == None:
            dialog = dialogform.UserPasswordForm(d)
            r = dialog.ShowDialog(self)
            if r != Forms.DialogResult.OK:
                return
        try:
            conn = fbutil.FbDatabase(d)
            conn.open()
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Can't open database")
            return
        node.Tag['User'] = d['User']
        node.Tag['Password'] = d['Password']
        node.Tag['SAVE_PASS_FLAG'] = d['SAVE_PASS_FLAG']
        node.Tag['CONNECTION'] = conn

        self.PopulateDBItems(node)

    def CloseDB(self, node):
        if node.Tag['CONNECTION']:
            node.Tag['CONNECTION'].close()
            node.Tag['CONNECTION'] = None
        node.Nodes.Clear()
        self.ChangeMenuEnabled(node)

    def FindAndCloseDB(self, server_node, database_name):
        for n in server_node.Nodes:
            if n.Tag['Database'] == database_name:
                self.CloseDB(n)

    def ReaderToGrid(self, reader):
        formutil.ReaderToGrid(self._dg, reader)

    def DictToGrid(self, d):
        formutil.DictToGrid(self._dg, d)

    def DictListToGrid(self, dlist):
        formutil.DictListToGrid(self._dg, dlist)

    def DomainsToGrid(self, conn):
        dl = []
        for c in conn.domains():
            dl.append({'NAME': c['NAME'].strip(),
                'TYPE': fbutil.fieldtype_to_string(c, False),
                'CHECK': c['VALIDATION_SOURCE'],
                'DEFAULT': c['DEFAULT_SOURCE'],
                'DESCRIPTION' : c['DESCRIPTION']})
        self.DictListToGrid(dl)

    def GrantUsersToGrid(self, conn, relation_name):
        dl = []
        for u in conn.grant_users(relation_name):
            d = {'NAME' : u['NAME']}
            if u['GRANT_OPTION'] == 2:
                d['ADMIN_OPTION'] = 'Yes'
            else:
                d['ADMIN_OPTION'] = 'No'
            dl.append(d)
        self.DictListToGrid(dl)

    def ColumnsToGrid(self, conn, viewname):
        columns = conn.columns(viewname)
        a = []
        for c in columns:
            a.append({'NAME':c['NAME'].strip(), 
                'TYPE':fbutil.fieldtype_to_string(c),
                'DESCRIPTION':c['DESCRIPTION']})
        formutil.DictListToGrid(self._dg, a)
        for i in range(self._dg.ColumnCount):
            self._dg.Columns[i].SortMode  = \
                                Forms.DataGridViewColumnSortMode.NotSortable

    def TableColumnsToGrid(self, conn, tabname, ri=0, ci=0):
        if is_Mono():
            formutil.ClearGrid(self._dg, 
                caps = ['NAME', 'TYPE', 'NOT NULL', 'DEFAULT', 'DESCRIPTION'])
        else:
            formutil.ClearGrid(self._dg, 
                caps = ['NAME', 'TYPE', 'DEFAULT', 'DESCRIPTION'])
            up = Forms.DataGridViewButtonColumn()
            up.HeaderText = 'Up'
            up.Text = 'Up'
            up.AutoSizeMode = Forms.DataGridViewAutoSizeColumnMode.DisplayedCells
            up.UseColumnTextForButtonValue = True
            self._dg.Columns.Insert(UP_BUTTON_COLUMN_INDEX, up)
            down = Forms.DataGridViewButtonColumn()
            down.HeaderText = 'Down'
            down.Text = 'Down'
            down.UseColumnTextForButtonValue = True
            self._dg.Columns.Insert(DOWN_BUTTON_COLUMN_INDEX, down)
            down.AutoSizeMode = Forms.DataGridViewAutoSizeColumnMode.DisplayedCells
    
            not_null = Forms.DataGridViewCheckBoxColumn()
            not_null.HeaderText = 'NOT NULL'
            not_null.AutoSizeMode = \
                            Forms.DataGridViewAutoSizeColumnMode.DisplayedCells
            self._dg.Columns.Insert(NOT_NULL_CHECK_COLUMN_INDEX, not_null)

        # Get key columns
        pk = []
        fk = []
        uk = []
        for r in conn.key_constraints_and_index(tabname):
            if r['CONST_TYPE'] == 'PRIMARY KEY':
                pk += r['FIELD_NAME']
            elif r['CONST_TYPE'] == 'FOREIGN KEY':
                fk += r['FIELD_NAME']
            elif r['CONST_TYPE'] == 'UNIQUE':
                uk += r['FIELD_NAME']

        columns = conn.columns(tabname)
        i = 0
        for c in columns:
            if is_Mono():
                if c['NULL_FLAG'] == 1:
                    null_flag = 'Yes'
                else:
                    null_flag = 'No'
                row = [c['NAME'].strip(), fbutil.fieldtype_to_string(c), 
                    null_flag,
                    fbutil.default_source_string(c), c['DESCRIPTION']]
            else:
                if c['NULL_FLAG'] == 1:
                    null_flag = 1
                else:
                    null_flag = 0
                row = [c['NAME'].strip(), fbutil.fieldtype_to_string(c), 
                    None, None, null_flag, 
                    fbutil.default_source_string(c), c['DESCRIPTION']]
            self._dg.Rows.Add(*row)
            if (row[0] in pk) and (row[0] in fk):
                for j in range(len(row)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = PK_FK_COLOR
            elif row[0] in pk:
                for j in range(len(row)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = PK_COLOR
            elif row[0] in fk:
                for j in range(len(row)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = FK_COLOR
            elif row[0] in uk:
                for j in range(len(row)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = UK_COLOR
            i += 1
        if i:
            self._dg.ClearSelection()
            self._dg.CurrentCell = self._dg.Rows[ri].Cells[ci]

        for i in range(self._dg.ColumnCount):
            self._dg.Columns[i].SortMode  = \
                                Forms.DataGridViewColumnSortMode.NotSortable

    def ProcedureParamsToGrid(self, conn, procname):
        a = []
        p = conn.procedure_source(procname)
        for in_p in p['IN_PARAMS']:
            a.append({'I/O': 'IN', 'NAME': in_p['NAME'],
                'TYPE':fbutil.fieldtype_to_string(in_p),
                'DESCRIPTION':in_p['DESCRIPTION']})
        for out_p in p['OUT_PARAMS']:
            a.append({'I/O': 'OUT', 'NAME': out_p['NAME'],
                'TYPE':fbutil.fieldtype_to_string(out_p),
                'DESCRIPTION':out_p['DESCRIPTION']})
        formutil.DictListToGrid(self._dg, a)
        for i in range(self._dg.ColumnCount):
            self._dg.Columns[i].SortMode  = \
                                Forms.DataGridViewColumnSortMode.NotSortable
    
    def SetDescriptionEditable(self):
        self._dg.EditMode = Forms.DataGridViewEditMode.EditOnKeystrokeOrF2
        for ri in range(self._dg.RowCount):
            for ci in range(self._dg.ColumnCount-1): # Last cell is DESCRIPTION
                self._dg.Rows[ri].Cells[ci].ReadOnly = True

    def __init__(self):
        self.dg_mode = None
        try:
            self.user_pref = formutil.userpref_load(USER_PROFILE)
        except:
            self.user_pref = {}

        # MenuStrip & MenuItem
        menu = [
            ['SERVERS', '&Servers', [
                ['REG_SERVER', 'Add &Server', self.OnRegServer], 
                ['UNREG_SERVER', '&Remove Server', self.OnRemoveServer],
                ['EDIT_SERVER', '&Edit Server info', self.OnEditServer], 
                ['-', '-', None],
                ['SERVER_LOG', 'Show Server &Log', self.OnServerLog], 
                ['-', '-', None],
                ['USERS_LIST', '&Users List', self.OnUsersList],
                ['USER_ADD', 'User &Add', self.OnUserAdd],
                ['-', '-', None],
                ['QUIT', '&Quit', self.OnQuit], 
            ]],
            ['DATABASES', '&Databases', [
                ['REG_DB', 'Register exsisting &Database', self.OnRegDB],
                ['UNREG_DB', '&Unregister Database', self.OnRemoveDB],
                ['REFRESH_TREE', 'Re&fresh Tree', self.OnRefreshTree],
                ['EDIT_DB', '&Edit Connect Parameter', self.OnEditDB],
                ['BACKUP_DB', '&Backup Databse', self.OnBackupRestoreDB],
                ['RESTORE_DB', '&Restore Databse', self.OnBackupRestoreDB],
                ['-', '-', None],
                ['CREATE_DB', 'Create &New database', self.OnCreateDB],
                ['OPEN_DB', '&Open Database', self.OnConnectDB],
                ['CLOSE_DB', '&Close Database', self.OnCloseDB],
                ['CREATE_TABLE', 'Create &Table', self.OnCreateTable],
            ]],
            ['TOOLS', '&Tools', [
                ['ISQL', 'Interactive &SQL', self.OnISQL],
                ['EXPORT_DDL', 'Export &DDL', self.OnExportDDL],
                ['-', '-', None],
            ]],
            ['OPTIONS', '&Options', [
                ['CONFIRM_SQL', '&Confirm SQL', self.OnConfirmSql],
            ]],
            ['HELP', '&Help', [
                ['ABOUT', '&About', self.OnAbout],
            ]],
        ]

        cmenu_top = [
            ['REG_SERVER', 'Add &Server', self.OnRegServer], 
            ['-', '-', None],
            ['QUIT', '&Quit', self.OnQuit], 
        ]

        cmenu_server = [
            ['EDIT_SERVER', '&Edit Server info', self.OnEditServer], 
            ['REG_DB', 'Register exsisting &database', self.OnRegDB],
            ['CREATE_DB', 'Create &new database', self.OnCreateDB],
            ['-', '-', None],
            ['SERVER_LOG', 'Show Server &Log', self.OnServerLog], 
            ['-', '-', None],
            ['USERS_LIST', '&Users List', self.OnUsersList],
            ['USER_ADD', 'User &Add', self.OnUserAdd],
            ['-', '-', None],
            ['UNREG_SERVER', '&Remove Server', self.OnRemoveServer], 
        ]

        cmenu_db = [
            ['REFRESH_TREE', 'Re&fresh Tree', self.OnRefreshTree],
            ['EDIT_DB', '&Edit connect parameter', self.OnEditDB],
            ['ISQL', 'Interactive &SQL', self.OnISQL],
            ['EXPORT_DDL', 'Export &DDL', self.OnExportDDL],
            ['BACKUP_DB', '&Backup database', self.OnBackupRestoreDB],
            ['RESTORE_DB', '&Restore database', self.OnBackupRestoreDB],
            ['OPEN_DB', '&Open database', self.OnConnectDB],
            ['CLOSE_DB', '&Close database', self.OnCloseDB],
            ['-', '-', None],
            ['IMPORT_MSSQL', 'Import from MS SQLServer(&1)', self.OnImportSQL],
            ['EXPORT_MSSQL', 'Export to MS SQLServer(&2)', self.OnExportSQL],
            ['IMPORT_ORACLE', 'Import from Oracle(&3)', self.OnImportOracle],
            ['EXPORT_ORACLE', 'Export to Oracle(&4)', self.OnExportOracle],
            ['IMPORT_SQLITE', 'Import from SQLite(&5)', self.OnImportSQLite],
            ['EXPORT_SQLITE', 'Export to SQLite(&6)', self.OnExportSQLite],
            ['-', '-', None],
            ['UNREG_DB', '&Unregister database', self.OnRemoveDB],
        ]

        cmenu_domains = [
            ['CREATE_DOMAIN', 'Create &Domain', self.OnCreateDomain],
        ]

        cmenu_domain = [
            ['RENAME_DOMAIN', '&Rename Domain', self.OnRenameDomain],
            ['CHANGE_TYPE_DOMAIN', 'Change Domain &Type', self.OnChangeTypeDomain],
            ['SET_DEFAULT_DOMAIN', '&Set Domain Default', self.OnSetDefaultDomain],
            ['ADD_CHECK_DOMAIN', 'Set Domain &Check Constraint', self.OnAddCheckDomain],
            ['DROP_DOMAIN', '&Drop Domain', self.OnDropDomain],
        ]

        cmenu_exceptions = [
            ['CREATE_EXCEPTION', 'Create &Exception', self.OnCreateException],
        ]

        cmenu_functions = [
            ['CREATE_FUNCTION', 'Create &Function', self.OnCreateFunction],
        ]

        cmenu_generators = [
            ['CREATE_GENERATOR', 'Create &Generator', self.OnCreateGenerator],
        ]

        cmenu_generator = [
            ['SET_GENERATOR', '&Set Generator', self.OnSetGenerator],
            ['DROP_GENERATOR', '&Drop Generator', self.OnDropGenerator],
        ]

        cmenu_procedures = [
            ['CREATE_PROCEDURE', 'Create &Procedure', self.OnCreateProcedure],
        ]

        cmenu_procedure = [
            ['PROCEDURE_SOURCE', '&Edit Source', self.OnProcedureSource],
            ['DROP_PROCEDURE', '&Drop Procedure', self.OnDropProcedure],
            ['SHOW_GRANT', 'Show Grant &Users', self.OnShowGrant],
            ['GRANT_PROCEDURE', '&Grant', self.OnGrantProcedure],
        ]

        cmenu_roles = [
            ['CREATE_ROLE', 'Create &Role', self.OnCreateRole],
        ]

        cmenu_role = [
            ['GRANT_ROLE', 'Grant &Role', self.OnGrantRole],
        ]

        cmenu_systemtable = [
            ['DATASYSTEMTABLE', '&Select * from ...', self.OnDataSystemTable],
        ]

        cmenu_tables = [
            ['CREATE_TABLE', 'Create &Table', self.OnCreateTable],
        ]

        cmenu_table = [
            ['DATATABLE', '&Select * from ...', self.OnDataTable],
            ['TABLE_CONSTRAINTS', 'Show &Constraints', self.OnTableConstraints],
            ['SHOW_INDEX', 'Show Inde&x', self.OnShowIndex],
            ['COPY_TABLE', 'Copy Table &to ...', self.OnCopyTable],
            ['DROP_TABLE', '&Drop Table', self.OnDropTable],
            ['GEN_TRIGGER', 'Create &New Generator and Trigger', 
                self.OnCreateGeneratorAndTrigger],
            ['ADD_COLUMN', '&Add Column', self.OnAddColumn],
            ['ADD_PRIMARY_KEY', 'Add &Primary Key', self.OnAddPrimaryKey],
            ['SHOW_REFERENCED_COLUMNS', 'Show &Referenced Table', 
                self.OnShowReferencedColumns],
            ['SHOW_GRANT', 'Show Grant &Users', self.OnShowGrant],
            ['GRANT_RELATION', '&Grant', self.OnGrantRelation],
        ]

        cmenu_columns = [
            ['RENAME_COLUMN', '&Rename column', self.OnRenameColumn],
            ['SET_DEFAULT', '&Set default', self.OnSetDefault],
            ['DROP_DEFAULT', 'Drop &default', self.OnDropDefault],
            ['RETYPE_COLUMN', '&Change column type', self.OnChangeColumnType],
            ['DROP_COLUMN', '&Drop column', self.OnDropColumn],
            ['CREATE_INDEX', 'Create Inde&x', self.OnCreateIndex],
            ['ADD_UNIQUE', 'Add &Unique constraint', self.OnAddUnique],
            ['ADD_FOREING_KEY', 'Add &Foreing key', self.OnAddForeignKey],
        ]

        cmenu_trigger = [
            ['TRIGGER_ACTIVATE', '&Activate', self.OnTriggerActivate],
            ['TRIGGER_INACTIVATE', '&Inactivate', self.OnTriggerInactivate],
            ['TRIGGER_SOURCE', '&Edit Source', self.OnTriggerSource],
            ['TRIGGER_SOURCE', '&Drop Trigger', self.OnDropTrigger],
        ]

        cmenu_views = [
            ['CREATE_VIEW', 'Create &View', self.OnCreateView],
        ]

        cmenu_view = [
            ['DATATABLE', '&Select * from ...', self.OnDataView],
            ['VIEW_SOURCE', '&Edit Source', self.OnViewSource],
            ['DROP_VIEW', '&Drop View', self.OnDropView],
            ['SHOW_GRANT', 'Show Grant &Users', self.OnShowGrant],
            ['GRANT_RELATION', '&Grant', self.OnGrantRelation],
        ]

        self.SuspendLayout()
        self._menu= Forms.MenuStrip()
        self._menu.Dock = Forms.DockStyle.Top
        self._menu.TabIndex = 1
        self.menu = formutil.build_menu(self._menu, menu)
        if int(self.user_pref.get('CONFIRM_SQL', '0')):
            self.menu['CONFIRM_SQL'].Checked = True

        self._cmenu_top = Forms.ContextMenuStrip()
        self.cmenu_top = formutil.build_context_menu(self._cmenu_top, cmenu_top)
        self._cmenu_server = Forms.ContextMenuStrip()
        self.cmenu_server = formutil.build_context_menu(
                                            self._cmenu_server, cmenu_server)
        self._cmenu_db = Forms.ContextMenuStrip()
        self.cmenu_db = formutil.build_context_menu(self._cmenu_db, cmenu_db)

        self._cmenu_domains = Forms.ContextMenuStrip()
        self.cmenu_domains = formutil.build_context_menu(
                                            self._cmenu_domains, cmenu_domains)

        self._cmenu_domain = Forms.ContextMenuStrip()
        self.cmenu_domain = formutil.build_context_menu(
                                            self._cmenu_domain, cmenu_domain)

        self._cmenu_exceptions = Forms.ContextMenuStrip()
        self.cmenu_exceptions = formutil.build_context_menu(
                                    self._cmenu_exceptions, cmenu_exceptions)

        self._cmenu_functions = Forms.ContextMenuStrip()
        self.cmenu_functions = formutil.build_context_menu(
                                    self._cmenu_functions, cmenu_functions)

        self._cmenu_generators = Forms.ContextMenuStrip()
        self.cmenu_generators = formutil.build_context_menu(
                                    self._cmenu_generators, cmenu_generators)

        self._cmenu_generator = Forms.ContextMenuStrip()
        self.cmenu_generator = formutil.build_context_menu(
                                    self._cmenu_generator, cmenu_generator)

        self._cmenu_procedures = Forms.ContextMenuStrip()
        self.cmenu_procedures = formutil.build_context_menu(
                                    self._cmenu_procedures, cmenu_procedures)

        self._cmenu_procedure = Forms.ContextMenuStrip()
        self.cmenu_procedure = formutil.build_context_menu(
                                        self._cmenu_procedure, cmenu_procedure)

        self._cmenu_roles = Forms.ContextMenuStrip()
        self.cmenu_roles = formutil.build_context_menu(
                                                self._cmenu_roles, cmenu_roles)

        self._cmenu_role = Forms.ContextMenuStrip()
        self.cmenu_role = formutil.build_context_menu(
                                                self._cmenu_role, cmenu_role)

        self._cmenu_systemtable = Forms.ContextMenuStrip()
        self.cmenu_systemtable = formutil.build_context_menu(
                                self._cmenu_systemtable, cmenu_systemtable)

        self._cmenu_tables = Forms.ContextMenuStrip()
        self.cmenu_tables = formutil.build_context_menu(
                                            self._cmenu_tables, cmenu_tables)

        self._cmenu_table = Forms.ContextMenuStrip()
        self.cmenu_table = formutil.build_context_menu(
                                            self._cmenu_table, cmenu_table)

        self._cmenu_columns = Forms.ContextMenuStrip()
        self.cmenu_columns = formutil.build_context_menu(
                                            self._cmenu_columns, cmenu_columns)
        
        self._cmenu_views = Forms.ContextMenuStrip()
        self.cmenu_views = formutil.build_context_menu(
                                            self._cmenu_views, cmenu_views)

        self._cmenu_view = Forms.ContextMenuStrip()
        self.cmenu_view = formutil.build_context_menu(
                                            self._cmenu_view, cmenu_view)

        self._cmenu_trigger = Forms.ContextMenuStrip()
        self.cmenu_trigger = formutil.build_context_menu(
                                            self._cmenu_trigger, cmenu_trigger)

        # Tree View
        self._tv = Forms.TreeView()
        try:
            il = Forms.ImageList()
            for f in img_files:
                il.Images.Add(Image.FromFile('res/' + f + '.png'))
            self._tv.ImageList = il
        except:
            pass
        self._tv.Dock = Forms.DockStyle.Fill
        self._tv.NodeMouseClick += self.OnNodeMouseClick 
        self._tv.NodeMouseClick += self.OnTreeViewSelect
        self._tv.AfterSelect += self.OnTreeViewSelect
        self._tv.NodeMouseDoubleClick += self.OnNodeMouseDoubleClick
        self._tv.TabIndex = 2

        # Data Grid View
        self._dg = Forms.DataGridView()
        System.ComponentModel.ISupportInitialize.BeginInit(self._dg)
        self._dg.DefaultCellStyle.NullValue = '<Null>'
        self._dg.ColumnHeadersHeightSizeMode = \
                Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
        self._dg.AutoGenerateColumns = True
        self._dg.AutoSizeRowsMode = \
                Forms.DataGridViewAutoSizeRowsMode.DisplayedCellsExceptHeaders
        self._dg.AutoSizeColumnsMode = \
                Forms.DataGridViewAutoSizeColumnsMode.AllCells
        self._dg.Dock = Forms.DockStyle.Fill
        self._dg.CellContentClick += self.OnGridCellContentClick
        self._dg.RowValidated += self.OnRowValidated
        self._dg.CellValueChanged += self.OnCellValueChanged
        self._dg.RowsAdded += self.OnRowsAdded
        self._dg.UserDeletingRow += self.OnUserDeletingRow
        self._dg.DataError += self.OnDataGridViewDataError
        self._dg.TabIndex = 3
        self._tv.BeginUpdate()
        self.load_tree()
        self._tv.EndUpdate()
        System.ComponentModel.ISupportInitialize.EndInit(self._dg)

        # SplitContainer
        self._split = Forms.SplitContainer()
        self._split.Dock = Forms.DockStyle.Fill
        self._split.Panel1.Controls.Add(self._tv)
        self._split.Panel2.Controls.Add(self._dg)
        self._split.SplitterDistance = 50 # Real value is 150, why 1/3 ?

        # Form
        self.Text = APP_NAME
        self.AutoScaleMode = Forms.AutoScaleMode.Font
        self.ClientSize = Size(self.user_pref.get('MAIN_WIDTH', 600), 
                                        self.user_pref.get('MAIN_HEIGHT', 400))
        self.Controls.Add(self._split)
        self.Controls.Add(self._menu)
        self.MainMenuStrip = self._menu
        self.ResumeLayout(False)
        self.PerformLayout()
        self.Closed += self.OnClose

    @eventhook
    def OnNodeMouseClick(self, sender, args):
        if args.Button == Forms.MouseButtons.Right:
            self._tv.SelectedNode = args.Node

    @eventhook
    def OnTreeViewSelect(self, sender, args):
        node = self.select_node(sender, args)
        if not node:
            self.dg_mode = None
            formutil.ClearGrid(self._dg)
            return
        if is_Mono():   # Disable delegation
            self._dg.CellValueChanged -= self.OnCellValueChanged
        self.ChangeMenuEnabled(node)
        self.dg_mode = node.Tag['NODE_TYPE']
        if self.dg_mode == 'INFO':
            self.DictToGrid(self.conn_from_node(node).info())
        elif self.dg_mode == 'TABLES':
            self.ReaderToGrid(self.conn_from_node(node).tables())
            self.SetDescriptionEditable()
        elif self.dg_mode == 'VIEWS':
            self.ReaderToGrid(self.conn_from_node(node).views())
            self.SetDescriptionEditable()
        elif self.dg_mode == 'DOMAINS':
            self.DomainsToGrid(self.conn_from_node(node))
            self.SetDescriptionEditable()
        elif self.dg_mode == 'ROLES':
            self.ReaderToGrid(self.conn_from_node(node).roles())
        elif self.dg_mode == 'ROLE':
            self.GrantUsersToGrid(self.conn_from_node(node), node.Name)
        elif self.dg_mode == 'EXCEPTIONS':
            self.ReaderToGrid(self.conn_from_node(node).exceptions())
            self.SetDescriptionEditable()
        elif self.dg_mode == 'GENERATORS':
            self.DictListToGrid(self.conn_from_node(node).generators())
        elif self.dg_mode == 'PROCEDURES':
            self.ReaderToGrid(self.conn_from_node(node).procedures())
            self.SetDescriptionEditable()
        elif self.dg_mode == 'TRIGGERS':
            self.ReaderToGrid(self.conn_from_node(node).triggers())
        elif self.dg_mode == 'FUNCTIONS':
            self.ReaderToGrid(self.conn_from_node(node).function_names())
            self.SetDescriptionEditable()
        elif self.dg_mode == 'SYSTEMTABLE':
            self.ColumnsToGrid(self.conn_from_node(node), node.Name)
        elif self.dg_mode == 'TABLE':
            self.TableColumnsToGrid(self.conn_from_node(node), node.Name)
            self.SetDescriptionEditable()
        elif self.dg_mode == 'VIEW':
            self.ColumnsToGrid(self.conn_from_node(node), node.Name)
            self.SetDescriptionEditable()
        elif self.dg_mode == 'PROCEDURE':
            self.ProcedureParamsToGrid(self.conn_from_node(node), node.Name)
            self.SetDescriptionEditable()
        elif self.dg_mode == 'KEY_CONSTRAINTS':
            self.DictListToGrid(self.conn_from_node(
                        node).key_constraints_and_index(node.Parent.Name))
        elif self.dg_mode == 'CHECK_CONSTRAINTS':
            self.DictListToGrid(self.conn_from_node(
                        node).check_constraints(node.Parent.Name))
        else:
            formutil.ClearGrid(self._dg)
        if is_Mono():   # Enable delegation
            self._dg.CellValueChanged += self.OnCellValueChanged

    @eventhook
    def OnDataGridViewDataError(self, sender, args):
        if self.dg_mode == 'TABLE_DATA' and \
            args.Exception and args.Exception.Message != 'UserWarning':
            Forms.MessageBox.Show(args.Exception.Message, 'Error')

    @eventhook
    def OnGridCellContentClick(self, sender, args):
        node = self.select_node(sender, args)
        ri = args.RowIndex
        ci = args.ColumnIndex
        if self.dg_mode == 'TABLE':
            if is_Mono():
                return
            conn = self.conn_from_node(node)
            if (ci == UP_BUTTON_COLUMN_INDEX or ci == DOWN_BUTTON_COLUMN_INDEX):
                cols = [c['NAME'].strip() for c in conn.columns(node.Text)]
                cn = cols[ri]
                if ci == UP_BUTTON_COLUMN_INDEX:
                    i = ri -1
                else:   # DOWN_BUTTON_COLUMN_INDEX
                    i = ri + 1
                if i < 0:
                    i = 0               # Force top
                elif i == len(cols):
                    i = len(cols) -1    # Force bottom
                cols.remove(cn)
                cols.insert(i, cn)
                conn.reorder_fields(node.Text, cols)
                self.TableColumnsToGrid(conn, node.Text, i, ci)
            elif ci == NOT_NULL_CHECK_COLUMN_INDEX:
                tab_name = node.Text
                col_name = self._dg.Rows[ri].Cells[0].Value
                if self._dg.Rows[ri].Cells[ci].Value:
                    not_null = False
                else:
                    not_null = True
                error = conn.set_not_null(tab_name, col_name, not_null, True)
                if error:
                    Forms.MessageBox.Show(error, 'Error')
                else:
                    self._dg.Rows[ri].Cells[ci].Value = not_null
        elif self.dg_mode == 'USERS_LIST':
            if ci == MOD_USER_BUTTON_COLUMN_INDEX:
                d = self.node_to_conndict(node)
                if not d:
                    return
                dialog = dialogform.UserModForm(
                        self._dg.Rows[ri].Cells[0].Value,
                        self._dg.Rows[ri].Cells[1].Value,
                        self._dg.Rows[ri].Cells[2].Value,
                        self._dg.Rows[ri].Cells[3].Value)
                r = dialog.ShowDialog(self)
                if r != Forms.DialogResult.OK:
                    return
                if not node.Tag.get('AlreadyLogin', False):
                    dialog = dialogform.UserPasswordForm(d)
                    r = dialog.ShowDialog(self)
                    if r != Forms.DialogResult.OK:
                        return
                try:
                    fbutil.user_mod(
                        d, dialog._user.Text,
                        password=dialog._password.Text,
                        first=dialog._first.Text,
                        middle=dialog._middle.Text,
                        last=dialog._last.Text)
                except Exception, e:
                    Forms.MessageBox.Show(str(e), "Error")
                    return
                if self.dg_mode == 'USERS_LIST':
                    self.OnUsersList(sender, args)
                node.Tag['User'] = d['User']
                node.Tag['Password'] = d['Password']
                node.Tag['SAVE_PASS_FLAG'] = d.get('SAVE_PASS_FLAG', '0')
                node.Tag['AlreadyLogin'] = True

    @eventhook
    def OnColumnChanging(self, sender, args):
        node = self.select_node(sender, args)
        if self.dg_mode == 'TABLE_DATA':
            if self._dg.CurrentRow.Cells[0].Style.BackColor == INPUT_COLOR:
                return
            conn = self.conn_from_node(node)
            cond = ''
            for i in range(len(self._dg.DataSource.DataSource.Columns)):
                cname = self._dg.DataSource.DataSource.Columns[i].ColumnName
                if cname in self.table_pks:
                    if len(cond):
                        cond += ' and '
                    cond += fbutil.expr_sql(cname, args.Row[i], 
                        self.table_type_array[i])
            sql = 'update "' + node.Name + '" set ' + \
                fbutil.expr_sql(args.Column.ColumnName, args.ProposedValue, 
                    self.table_type_dict[args.Column.ColumnName]) + \
                ' where ' + cond
            if not self.ConfirmSql(conn, sql):
                raise UserWarning, "Abort change value."

    @eventhook
    def OnRowValidated(self, sender, args):
        node = self.select_node(sender, args)
        conn = self.conn_from_node(node)
        tab_name = node.Name
        if self.dg_mode == 'TABLE_DATA':
            ri = args.RowIndex
            if self._dg.Rows[ri].Cells[0].Style.BackColor == INPUT_COLOR:
                cnames = []
                values = []
                for ci in range(self._dg.ColumnCount):
                    if not IsDBNull(self._dg.Rows[ri].Cells[ci].Value):
                        cnames.append(self._dg.Columns[ci].Name)
                        values.append(fbutil.expr_sql(None, 
                            self._dg.Rows[ri].Cells[ci].Value, 
                            self.table_type_array[ci]))
                sql = 'insert into "' + tab_name + '" ("' 
                sql += '","'.join(cnames)
                sql += '") values (' + ','.join(values) + ')'

                if self.ConfirmSql(conn, sql):
                    pks =  conn.primary_keys(tab_name)
                    if set(pks) - set(cnames) != set([]):
                        read_only = True
                    else:
                        read_only = False
                    for ci in range(self._dg.ColumnCount):
                        cell = self._dg.Rows[ri].Cells[ci]
                        cell.Style.BackColor = NEW_DATA_COLOR
                        if read_only:
                            cell.ReadOnly = True

    @eventhook
    def OnCellValueChanged(self, sender, args):
        if self.dg_mode == 'TABLE_DATA':
            return
        node = self.select_node(sender, args)
        description = self._dg.Rows[args.RowIndex].Cells[args.ColumnIndex].Value
        name = self._dg.Rows[args.RowIndex].Cells[0].Value.strip()
        if self.dg_mode == 'TABLE' or self.dg_mode == 'VIEW':
            sqlStmt = "update rdb$relation_fields " + \
                    "set rdb$description = '" + sqlquote(description) + "' " + \
                    "where rdb$field_name='" + name + "' " + \
                    "and rdb$relation_name='" + node.Name + "'" 
        elif self.dg_mode == 'PROCEDURE':
            sqlStmt = "update rdb$procedure_parameters " + \
                    "set rdb$description = '" + sqlquote(description) + "' " + \
                    "where rdb$parameter_name='" + name + "' " + \
                    "and rdb$procedure_name='" + node.Name + "'"
        else:
            if self.dg_mode == 'TABLES' or self.dg_mode == 'VIEWS':
                tab_name = 'rdb$relations'
                field_name = 'rdb$relation_name'
            elif self.dg_mode == 'FUNCTIONS':
                tab_name = 'rdb$functions'
                field_name = 'rdb$function_name'
            elif self.dg_mode == 'EXCEPTIONS':
                tab_name = 'rdb$exceptions'
                field_name = 'rdb$exception_name'
            elif self.dg_mode == 'DOMAINS':
                tab_name = 'rdb$fields'
                field_name = 'rdb$field_name'
            elif self.dg_mode == 'PROCEDURES':
                tab_name = 'rdb$procedures'
                field_name = 'rdb$procedure_name'
            sqlStmt = "update %s set rdb$description = '%s' where %s='%s'" % (
                tab_name, sqlquote(description), field_name, name)
        self.conn_from_node(node).execute_noq(sqlStmt)

    @eventhook
    def OnRowsAdded(self, sender, args):
        return
        if self.dg_mode == 'TABLE_DATA':
            ri = args.RowIndex - 1
            for ci in range(self._dg.ColumnCount):
                self._dg.Rows[ri].Cells[ci].Style.BackColor = INPUT_COLOR

    @eventhook
    def OnUserDeletingRow(self, sender, args):
        node = self.select_node(sender, args)
        if self.dg_mode == 'USERS_LIST':
            d = self.node_to_conndict(node)
            if not d:
                return
            fbutil.user_del(d, args.Row.Cells[0].Value)
            return
        elif self.dg_mode == 'DOMAINS':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "drop domain " + args.Row.Cells[0].Value
            ):
                self.PopulateDomains(node)
                return
        elif self.dg_mode == 'EXCEPTIONS':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "drop exception " + args.Row.Cells[0].Value.strip()
            ):
                return
        elif self.dg_mode == 'FUNCTIONS':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "drop external function " + args.Row.Cells[0].Value.strip()
            ):
                return
        elif self.dg_mode == 'GENERATORS':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "drop generator " + args.Row.Cells['NAME'].Value.strip()
            ):
                return
        elif self.dg_mode == 'PROCEDURES':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "drop procedure " + args.Row.Cells[0].Value.strip()
            ):
                return
        elif self.dg_mode == 'ROLES':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "drop role " + args.Row.Cells[0].Value.strip()
            ):
                return
        elif self.dg_mode == 'ROLE':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "revoke %s from %s" %
                (node.Name, args.Row.Cells[0].Value.strip())
            ):
                return
        elif self.dg_mode == 'TABLE_CONSTRAINTS':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "alter table %s drop constraint %s" %
                (node.Name, args.Row.Cells[0].Value)
            ):
                self.PopulateTable(node)
                return
        elif self.dg_mode == 'SHOW_INDEX':
            if self.ConfirmSql(
                self.conn_from_node(node),
                "drop index %s " % (args.Row.Cells[0].Value)
            ):
                return
        elif self.dg_mode == 'TABLES':
            if self.ConfirmSql(
                self.conn_from_node(node),
                'drop tbale "%s"' % args.Row.Cells[0].Value.strip()
            ):
                self.PopulateTables(node)
                return
        elif self.dg_mode == 'TABLE':
            if self.ConfirmSql(
                self.conn_from_node(node),
                'alter table "%s" drop "%s"' %
                (node.Name, args.Row.Cells[0].Value.strip())
            ):
                self.PopulateTable(node)
                return
        elif self.dg_mode == 'VIEWS':
            if self.ConfirmSql(
                self.conn_from_node(node),
                'drop view "%s"' % (args.Row.Cells[0].Value.strip(),)
            ):
                self.PopulateViews(node)
                return
        elif self.dg_mode == 'TABLE_DATA':
            if args.Row.Cells[0].Style.BackColor == INPUT_COLOR:
                return
            conn = self.conn_from_node(node)
            pks = conn.primary_keys(node.Name)
            t = [c['TYPE_NAME'].strip() for c in conn.columns(node.Name)]
            if len(pks):
                cond = ''
                for i in range(len(self._dg.DataSource.DataSource.Columns)):
                    cname = self._dg.DataSource.DataSource.Columns[i].ColumnName
                    if cname in pks:
                        if IsDBNull(args.Row.Cells[i].Value):
                            raise UserWarning("Can't delete.")
                        if len(cond):
                            cond += ' and '
                        cond += fbutil.expr_sql(cname, args.Row.Cells[i].Value, t[i])
                if self.ConfirmSql(
                    self.conn_from_node(node),
                    'delete from "' + node.Name + '" where ' + cond
                ):
                    return
        elif self.dg_mode == 'SHOW_GRANT_RELATION':
            if len(args.Row.Cells) == 4 and args.Row.Cells[2].Value:
                sql = "revoke "
                sql += ','.join(
                    [s + '(' + args.Row.Cells[2].Value + ')' for s in args.Row.Cells[1].Value.split(',')]
                )
                sql += ' on ' + node.Name + " from " + args.Row.Cells[0].Value
            else:
                sql = "revoke %s on %s from %s" % (
                    args.Row.Cells[1].Value, node.Name, args.Row.Cells[0].Value)
            if self.ConfirmSql(self.conn_from_node(node), sql):
                return
        elif self.dg_mode == 'SHOW_GRANT_PROCEDURE':
            if (
                self.ConfirmSql(
                    self.conn_from_node(node),
                    "revoke %s on procedure %s from %s" %
                    (args.Row.Cells[1].Value, node.Name, args.Row.Cells[0].Value))
            ):
                return

        args.Cancel = True

    @eventhook
    def OnNodeMouseDoubleClick(self, sender, args):
        node = self.select_node(sender, args)
        if node.Tag['NODE_TYPE'] == 'DATABASE':
            self.ConnectDB(node)
        elif node.Tag['NODE_TYPE'] == 'GENERATORS':
            self.PopulateGenerators(node)
        elif node.Tag['NODE_TYPE'] == 'PROCEDURES':
            self.PopulateProcedures(node)
        elif node.Tag['NODE_TYPE'] == 'TABLE':
            self.PopulateTable(node)

    @eventhook
    def OnRegServer(self, sender, args):
        dialog = dialogform.ServerPropForm()
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            for node in self._tv.Nodes[0].Nodes:
                if node.Text == dialog._alias.Text:
                    Forms.MessageBox.Show('Server "%s is already exists.' % (dialog._alias.Text,), 'Error')
                    return
            img = self.imgidx('server')
            node = Forms.TreeNode(dialog._alias.Text, img, img)
            node.ContextMenuStrip = self._cmenu_server
            node.Tag = {
                'NODE_TYPE': 'SERVER',
                'SERVER': dialog._server.Text,
            }
            self._tv.BeginUpdate()
            self._tv.Nodes[0].Nodes.Add(node)
            self._tv.EndUpdate()

    @eventhook
    def OnEditServer(self, sender, args):
        node = self.select_node(sender, args, node_type='SERVER')
        alias_name = node.Text
        server_name = node.Tag['SERVER']
        dialog = dialogform.ServerPropForm(alias_name, server_name)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._tv.SelectedNode.Text = dialog._alias.Text
            self._tv.SelectedNode.Tag['SERVER'] = dialog._server.Text

    @eventhook
    def ServerLogHandler(self, o, e):
        self._dg.Rows.Add(e.Message)

    @eventhook
    def OnServerLog(self, sender, args):
        node = self.select_node(sender, args, node_type='SERVER')
        formutil.ClearGrid(self._dg, caps=['Messages'])
        d = self.node_to_conndict(node)
        if not d:
            return
        if not node.Tag.get('AlreadyLogin', False):
            dialog = dialogform.UserPasswordForm(d)
            r = dialog.ShowDialog(self)
            if r != Forms.DialogResult.OK:
                return
        try:
            fbutil.server_log(d, self.ServerLogHandler)
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Can't get log")
            return
        node.Tag['User'] = d['User']
        node.Tag['Password'] = d['Password']
        node.Tag['SAVE_PASS_FLAG'] = d.get('SAVE_PASS_FLAG', '0')
        node.Tag['AlreadyLogin'] = True
        self.dg_mode = 'SERVER_LOG'

    @eventhook
    def OnUsersList(self, sender, args):
        node = self.select_node(sender, args, node_type='SERVER')
        d = self.node_to_conndict(node)
        if not d:
            return
        if not node.Tag.get('AlreadyLogin', False):
            dialog = dialogform.UserPasswordForm(d)
            r = dialog.ShowDialog(self)
            if r != Forms.DialogResult.OK:
                return
        try:
            a = fbutil.users_list(d)
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Error")
            return
        self.DictListToGrid(a)
        if not is_Mono():
            mod = Forms.DataGridViewButtonColumn()
            mod.HeaderText = 'Modfy'
            mod.Text = 'Modify'
            mod.AutoSizeMode = Forms.DataGridViewAutoSizeColumnMode.DisplayedCells
            mod.UseColumnTextForButtonValue = True
            self._dg.Columns.Insert(MOD_USER_BUTTON_COLUMN_INDEX, mod)

        node.Tag['User'] = d['User']
        node.Tag['Password'] = d['Password']
        node.Tag['SAVE_PASS_FLAG'] = d.get('SAVE_PASS_FLAG', '0')
        node.Tag['AlreadyLogin'] = True
        self.dg_mode = 'USERS_LIST'

    @eventhook
    def OnUserAdd(self, sender, args):
        node = self.select_node(sender, args, node_type='SERVER')
        d = self.node_to_conndict(node)
        if not d:
            return
        dialog = dialogform.UserAddForm()
        r = dialog.ShowDialog(self)
        if r != Forms.DialogResult.OK:
            return
        if not node.Tag.get('AlreadyLogin', False):
            dialog = dialogform.UserPasswordForm(d)
            r = dialog.ShowDialog(self)
            if r != Forms.DialogResult.OK:
                return
        fbutil.user_add(
            d, dialog._user.Text, dialog._password.Text,
            first=dialog._first.Text, middle=dialog._middle.Text,
            last=dialog._last.Text)
        if self.dg_mode == 'USERS_LIST':
            self.OnUsersList(sender, args)
        node.Tag['User'] = d['User']
        node.Tag['Password'] = d['Password']
        node.Tag['SAVE_PASS_FLAG'] = d.get('SAVE_PASS_FLAG', '0')
        node.Tag['AlreadyLogin'] = True

    @eventhook
    def OnRemoveServer(self, sender, args):
        node = self.select_node(sender, args, node_type='SERVER')
        for n in node.Nodes:
            self.CloseDB(n)
        self._tv.Nodes.Remove(node)

    @eventhook
    def OnRemoveDB(self, sender, args):
        node = self.select_node(sender, args, node_type='DATABASE')
        self.CloseDB(node)
        self._tv.Nodes.Remove(node)

    @eventhook
    def OnConfirmSql(self, sender, args):
        if sender.Checked:
            sender.Checked = False
        else:
            sender.Checked = True

    @eventhook
    def OnAbout(self, sender, args):
        s = [APP_NAME, ' ', __version__, '\n', 'Python', sys.version]
        Forms.MessageBox.Show(''.join(s), 'Version')

    @eventhook
    def OnRegDB(self, sender, args):
        node = self.select_node(sender, args, node_type='SERVER')
        dialog = dialogform.ConnPropForm()
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateDB(node, dialog.conn_d)

    @eventhook
    def OnRefreshTree(self, sender, args):
        node = self.select_node(sender, args, node_type='DATABASE')
        self.PopulateDBItems(node)

    @eventhook
    def OnEditDB(self, sender, args, node_type='DATABASE'):
        node = self.select_node(sender, args, node_type='DATABASE')
        dialog = dialogform.ConnPropForm(conn_d=node.Tag)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            node.Text = dialog.conn_d['DISPLAY_NAME']
            node.Tag.update(dialog.conn_d)

    @eventhook
    def OnISQL(self, sender, args, node_type='DATABASE'):
        node = self.select_node(sender, args, node_type='DATABASE')
        d = self.node_to_conndict(node)
        if not d:
            return
        if d['Password'] is None:
            dialog = dialogform.UserPasswordForm(d)
            r = dialog.ShowDialog(self)
            if r != Forms.DialogResult.OK:
                return
        FbSqlForm.FbSqlForm(d, self.user_pref).Show(self)

    @eventhook
    def OnExportDDL(self, sender, args, node_type='DATABASE'):
        node = self.select_node(sender, args, node_type='DATABASE')
        d = self.node_to_conndict(node)
        if not d:
            return
        if d['Password'] is None:
            dialog = dialogform.UserPasswordForm(d)
            r = dialog.ShowDialog(self)
            if r != Forms.DialogResult.OK:
                return
        try:
            dialogform.SimpleTextForm('DDL', fbddl.get_ddl(d)).Show()
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Error")

    @eventhook
    def OnBackupRestoreDB(self, sender, args):
        node = self.select_node(sender, args, node_type='DATABASE')
        d = self.node_to_conndict(node)
        if not d:
            return
        dialog = BackupRestoreForm(
            d, node.Tag.get('BACKUP_FILENAME'), sender.Tag == 'BACKUP_DB')
        dialog.ShowDialog(self)
        if dialog.conn_d.get('PrevUser'):
            node.Tag['User'] = dialog.conn_d['User']
            node.Tag['Password'] = dialog.conn_d['Password']
        node.Tag['BACKUP_FILENAME'] = dialog._filePath.Text

    @eventhook
    def OnConnectDB(self, sender, args):
        self.ConnectDB(self.select_node(sender, args))

    @eventhook
    def OnCloseDB(self, sender, args):
        self.CloseDB(self.select_node(sender, args, node_type='DATABASE'))

    @eventhook
    def OnCreateDomain(self, sender, args):
        node = self.select_node(sender, args, node_type='DOMAINS')
        sql = """create domain XXXXX
    as integer
    default 1000000
    check (value > 0);"""
        d = self.node_to_conndict(node.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateDomains(node)
            self.DomainsToGrid(self.conn_from_node(node))

    @eventhook
    def OnRenameDomain(self, sender, args):
        node = self.select_node(sender, args, node_type='DOMAIN')
        for r in self.conn_from_node(node).domains(node.Name):  # only one
            sql = 'alter domain ' + r['NAME'].strip() + '\n'
            sql += '    to new_' + r['NAME'].strip() + '\n'
            d = self.node_to_conndict(node.Parent.Parent)
            dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
            r = dialog.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                node = node.Parent
                self.PopulateDomains(node)
                self.DomainsToGrid(self.conn_from_node(node))

    @eventhook
    def OnChangeTypeDomain(self, sender, args):
        node = self.select_node(sender, args, node_type='DOMAIN')
        for r in self.conn_from_node(node).domains(node.Name):  # only one
            sql = 'alter domain ' + r['NAME'].strip() + '\n'
            sql += '    type ' + fbutil.fieldtype_to_string(r) + '\n'
            d = self.node_to_conndict(node.Parent.Parent)
            dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
            r = dialog.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                node = node.Parent
                self.PopulateDomains(node)
                self.DomainsToGrid(self.conn_from_node(node))

    @eventhook
    def OnSetDefaultDomain(self, sender, args):
        node = self.select_node(sender, args, node_type='DOMAIN')
        for r in self.conn_from_node(node).domains(node.Name):  # only one
            sql = 'alter domain ' + r['NAME'].strip() + ' drop default;\n'
            sql += 'alter domain ' + r['NAME'].strip() + '\n    set '
            if IsDBNull(r['DEFAULT_SOURCE']):
                sql += 'default NULL'
            else:
                sql += r['DEFAULT_SOURCE']
            d = self.node_to_conndict(node.Parent.Parent)
            dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
            r = dialog.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                node = node.Parent
                self.PopulateDomains(node)
                self.DomainsToGrid(self.conn_from_node(node))

    @eventhook
    def OnAddCheckDomain(self, sender, args):
        node = self.select_node(sender, args, node_type='DOMAIN')
        for r in self.conn_from_node(node).domains(node.Name):  # only one
            sql = 'alter domain ' + r['NAME'].strip() + ' drop constraint;\n'
            sql += 'alter domain ' + r['NAME'].strip() + '\n    add '
            if IsDBNull(r['VALIDATION_SOURCE']):
                sql += 'default NULL'
            else:
                sql += r['VALIDATION_SOURCE']
            d = self.node_to_conndict(node.Parent.Parent)
            dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
            r = dialog.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                node = node.Parent
                self.PopulateDomains(node)
                self.DomainsToGrid(self.conn_from_node(node))

    @eventhook
    def OnDropDomain(self, sender, args):
        node = self.select_node(sender, args, node_type='DOMAIN')
        if self.ConfirmSql(
            self.conn_from_node(node),
            "drop domain " + node.Name
        ):
            node = node.Parent
            self._tv.SelectedNode = node
            self.PopulateDomains(node)

    @eventhook
    def OnCreateException(self, sender, args):
        node = self.select_node(sender, args, node_type='EXCEPTIONS')
        d = self.node_to_conndict(node.Parent)
        dialog = FbSqlForm.FbSqlForm(
            d, self.user_pref,
            sql="create exception XXXXX\n    'XXXX Exception message'")
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.ReaderToGrid(self.conn_from_node(node).exceptions())

    @eventhook
    def OnCreateFunction(self, sender, args):
        node = self.select_node(sender, args, node_type='FUNCTIONS')
        sql = """declare external function string2blob
varchar(300) by descriptor,
blob returns parameter 2
entry_point 'string2blob' module_name 'fbudf';"""
        d = self.node_to_conndict(node.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.ReaderToGrid(self.conn_from_node(node).function_names())

    @eventhook
    def OnCopyTable(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        dialog = dialogform.CopyTableForm('New_' + node.Name)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            try:
                if self.conn_from_node(node).copy_table(
                    node.Name, dialog.text, dialog.schema_only
                ):
                    self.PopulateTables(node.Parent)
                    self._tv.SelectedNode = node.Parent
                else:
                    Forms.MessageBox.Show(
                        "Invalid name '%s'" % (dialog.text,), "Error")
            except Exception, e:
                Forms.MessageBox.Show(str(e), "Error")

    @eventhook
    def OnDropTable(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        if self.ConfirmSql(
            self.conn_from_node(node),
            'drop table "%s"' % (node.Name,)
        ):
            node = node.Parent
            self.PopulateTables(node)
            self.ReaderToGrid(self.conn_from_node(node).tables())

    @eventhook
    def OnRenameTable(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            'alter table "' + node.Text + '" rename to new_' + node.Text)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateTables(node.Parent)

    @eventhook
    def OnCreateGenerator(self, sender, args):
        node = self.select_node(sender, args, node_type='GENERATORS')
        dialog = dialogform.SimpleSqlForm(self.conn_from_node(node), "create generator XXXXX")
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateGenerators(node)

    @eventhook
    def OnSetGenerator(self, sender, args):
        node = self.select_node(sender, args, node_type='GENERATOR')
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            'set generator "%s" to %s' %
            (node.Name, str(self.conn_from_node(node).get_generator_id(node.Name)))
        )
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._tv.SelectedNode = node.Parent

    @eventhook
    def OnDropGenerator(self, sender, args):
        node = self.select_node(sender, args, node_type='GENERATOR')
        if self.ConfirmSql(self.conn_from_node(node), 'drop generator "%s"' % (node.Name,)):
            node = node.Parent
            self._tv.SelectedNode = node
            self.PopulateGenerators(node)

    @eventhook
    def OnCreateRole(self, sender, args):
        node = self.select_node(sender, args, node_type='ROLES')
        d = self.node_to_conndict(node.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql="create role XXXXX")
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.ReaderToGrid(self.conn_from_node(node).roles())

    @eventhook
    def OnGrantRole(self, sender, args):
        node = self.select_node(sender, args, node_type='ROLE')
        d = self.node_to_conndict(node.Parent.Parent)
        users = [u['NAME'].strip() for u in fbutil.users_list(d)]
        dialog = dialogform.SelectItemsForm('Select users', users)

        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            sql = 'grant ' + node.Name + ' to '
            sql += ','.join(dialog.selected)
            sql += ' with admin option'
            dialog2 = dialogform.SimpleSqlForm(self.conn_from_node(node), sql)
            r = dialog2.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                self.GrantUsersToGrid(self.conn_from_node(node), node.Name)

    @eventhook
    def OnShowGrant(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        if not node:
            node = self.select_node(sender, args, node_type='VIEW')
        if not node:
            node = self.select_node(sender, args, node_type='PROCEDURE')
        priv = {
            'S': 'SELECT',
            'D': 'DELETE',
            'I': 'INSERT',
            'U': 'UPDATE',
            'R': 'REFERENCES',
            'X': 'EXECUTE',
        }
        d = {}
        has_field_name = False
        for r in self.conn_from_node(node).grant_users(node.Name):
            d.setdefault(
                (r['NAME'].strip(), r['GRANT_OPTION'], r['FIELD_NAME']), []
            ).append(priv[r['PRIVILEGE'].strip()])
            if not IsDBNull(r['FIELD_NAME']):
                has_field_name = True
        dl = []
        for k in d:
            e = {
                'NAME': k[0],
                'PRIVILEGE': ','.join(d[k]),
            }
            if has_field_name:
                e['FIELD_NAME'] = k[2]
            if k[1] == 1:
                e['GRANT_OPTION'] = 'Yes'
            else:
                e['GRANT_OPTION'] = 'No'
            dl.append(e)
        self.DictListToGrid(dl)
        if node.Tag['NODE_TYPE'] == 'PROCEDURE':
            self.dg_mode = 'SHOW_GRANT_PROCEDURE'
        else:
            self.dg_mode = 'SHOW_GRANT_RELATION'

    @eventhook
    def OnGrantRelation(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        if not node:
            node = self.select_node(sender, args, node_type='VIEW')

        d = self.node_to_conndict(node.Parent.Parent)
        dialog = FbSqlForm.FbSqlForm(
            d, self.user_pref,
            sql='grant SELECT,DELETE,INSERT,UPDATE,REFERENCES on %s to SYSDBA with grant option' % (node.Name, )
        )
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.OnShowGrant(sender, args)

    @eventhook
    def OnGrantProcedure(self, sender, args):
        node = self.select_node(sender, args, node_type='PROCEDURE')
        d = self.node_to_conndict(node.Parent.Parent)
        dialog = FbSqlForm.FbSqlForm(
            d, self.user_pref,
            sql='grant EXECUTE on procedure %s to SYSDBA with grant option' % (node.Name,)
        )
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.OnShowGrant(sender, args)

    @eventhook
    def OnCreateTable(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLES')
        sql = """
create table XXXXX (
    ID integer not null,
    primary key (ID)
--  ,
--  C varchar(1024) not null unique,
--  F decimal(16,2) default 0.0,
--  D date default CURRENT_DATE,
--  T timestamp default CURRENT_TIMESTAMP,
--  B blob sub_type 0,
--  foreign key (C) references FOO_TABLE(BAR_COLUMN) on update cascade,
--  constraint CHECK_ID check (ID > 0)
)"""
        d = self.node_to_conndict(node.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateTables(node)
            self.ReaderToGrid(self.conn_from_node(node).tables())

    @eventhook
    def OnAddColumn(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            "alter table %s add XXXXX varchar(255)" % (node.Name)
        )
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateTable(node)

    @eventhook
    def OnAddPrimaryKey(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        conn = self.conn_from_node(node)
        if len(conn.primary_keys(node.Name)):
            Forms.MessageBox.Show(node.Name + ' has Primary Key(s).', "Error")
            return
        columns = [c['NAME'].strip() for c in conn.columns(node.Name)]
        dialog = dialogform.SelectItemsForm('Select columns', columns)

        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            sql = 'alter table ' + node.Name + ' add primary key('
            sql += ','.join(dialog.selected)
            sql += ')'
            dialog2 = dialogform.SimpleSqlForm(self.conn_from_node(node), sql)
            r = dialog2.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                self.PopulateTable(node)
                self.TableColumnsToGrid(self.conn_from_node(node), node.Name)

    @eventhook
    def OnShowReferencedColumns(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        conn = self.conn_from_node(node)
        self.ReaderToGrid(conn.referenced_columns(node.Name))
        self.dg_mode = 'REFERENCED_COLUMNS'

    @eventhook
    def OnRenameColumn(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            "alter table " + node.Parent.Name + " alter column " + node.Name
            + " to new_" + node.Name)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateTable(node.Parent)

    @eventhook
    def OnSetDefault(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            "alter table %s alter column set default XXXXX" %
            (node.Parent.Name, node.Name)
        )
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateTable(node.Parent)

    @eventhook
    def OnDropDefault(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        if self.ConfirmSql(
            self.conn_from_node(node),
            "alter table %s alter column %s drop default" %
            (node.Parent.Name, node.Name)
        ):
            self.PopulateTable(node.Parent)

    @eventhook
    def OnChangeColumnType(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        s = node.Text.split()
        s.insert(1, 'type')
        s = ' '.join(s)
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            "alter table %s alter columns %s" % (node.Parent.Name, s)
        )
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateTable(node.Parent)

    @eventhook
    def OnDropColumn(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        if self.ConfirmSql(
            self.conn_from_node(node),
            "alter table " + node.Parent.Name + " drop " + node.Name
        ):
            self.PopulateTable(node.Parent)

    @eventhook
    def OnCreateIndex(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            "create index %s_INDEX on %s(%s)" %
            (node.Name, node.Parent.Name, node.Name)
        )
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            pass

    @eventhook
    def OnAddUnique(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        tab_name = node.Parent.Name
        dialog = dialogform.SimpleSqlForm(
            self.conn_from_node(node),
            "alter table " + tab_name + " add unique(" + node.Name + ")")
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            pass

    @eventhook
    def OnAddForeignKey(self, sender, args):
        node = self.select_node(sender, args, node_type='COLUMN')
        tab_name = node.Parent.Name
        dialog = dialogform.TableColumnForm(
            'Select reference table & column.', self.conn_from_node(node))
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            dialog = dialogform.SimpleSqlForm(
                self.conn_from_node(node),
                """alter table %s  add foreign key(%s) references %s(%s)
                    on update cascade on delete cascade""" %
                (tab_name, node.Name, dialog.table_name, dialog.column_name)
            )
            r = dialog.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                pass

    @eventhook
    def OnDataSystemTable(self, sender, args):
        node = self.select_node(sender, args, node_type='SYSTEMTABLE')
        tab_name = node.Name
        data_adapter = self.conn_from_node(node).table_adapter(tab_name)
        columns = self.conn_from_node(node).columns(tab_name)
        data_table = DataTable()
        data_table.Clear()
        data_adapter.Fill(data_table)
        formutil.DataTableToGrid(self._dg, data_table, tab_name, columns)
        data_adapter.Dispose()
        self.dg_mode = 'SYSTEMTABLE_DATA'

    @eventhook
    def OnDataTable(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        tab_name = node.Name
        conn = self.conn_from_node(node)
        try:
            data_adapter = conn.table_adapter(tab_name)
            columns = conn.columns(tab_name)
            data_table = DataTable()
            data_table.ColumnChanging += self.OnColumnChanging
            data_table.Clear()
            data_adapter.Fill(data_table)
            formutil.DataTableToGrid(self._dg, data_table, tab_name, columns)
            data_adapter.Dispose()
            table_pks = conn.primary_keys(tab_name)
            table_fks = [
                fk['FIELD_NAME'].strip() for fk in conn.foreign_keys(tab_name)
            ]
            table_uks = conn.unique_keys(tab_name)
            td = {}
            ta = []
            if len(table_pks):
                self._dg.EditMode = \
                    Forms.DataGridViewEditMode.EditOnKeystrokeOrF2
                self._dg.AllowUserToAddRows = True
            for c in conn.columns(tab_name):
                td[c['NAME'].strip()] = c['TYPE_NAME'].strip()
                ta.append(c['TYPE_NAME'].strip())
            self.table_pks = table_pks
            self.table_type_array = ta
            self.table_type_dict = td
            for c in self._dg.Columns:
                if c.Name in self.table_pks and c.Name in table_fks:
                    c.DefaultCellStyle.BackColor = PK_FK_COLOR
                elif c.Name in self.table_pks:
                    c.DefaultCellStyle.BackColor = PK_COLOR
                elif c.Name in table_fks:
                    c.DefaultCellStyle.BackColor = FK_COLOR
                elif c.Name in table_uks:
                    c.DefaultCellStyle.BackColor = UK_COLOR
            self.dg_mode = 'TABLE_DATA'
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Error")

        for i in range(self._dg.ColumnCount):
            self._dg.Columns[i].SortMode = Forms.DataGridViewColumnSortMode.NotSortable

    @eventhook
    def OnCreateView(self, sender, args):
        node = self.select_node(sender, args, node_type='VIEWS')
        sql = "create view XXXXX as select * from TABLE_NAME"
        d = self.node_to_conndict(node.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateViews(node)
            self.ReaderToGrid(self.conn_from_node(node).views())

    @eventhook
    def OnDataView(self, sender, args):
        node = self.select_node(sender, args, node_type='VIEW')
        view_name = node.Text
        try:
            data_adapter = self.conn_from_node(node).table_adapter(view_name)
            columns = self.conn_from_node(node).columns(view_name)
            data_table = DataTable()
            data_table.Clear()
            data_adapter.Fill(data_table)
            formutil.DataTableToGrid(self._dg, data_table, view_name, columns)
            data_adapter.Dispose()
            self.dg_mode = 'VIEW_DATA'
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Error")

    @eventhook
    def OnViewSource(self, sender, args):
        node = self.select_node(sender, args, node_type='VIEW')
        sql = 'drop view %s;\ncreate view %s AS' % (node.Name, node.Name)
        sql += self.conn_from_node(node).view_source(node.Text)
        d = self.node_to_conndict(node.Parent.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.ColumnsToGrid(self.conn_from_node(node), node.Text)

    @eventhook
    def OnDropView(self, sender, args):
        node = self.select_node(sender, args, node_type='VIEW')
        if self.ConfirmSql(self.conn_from_node(node), "drop view " + node.Name):
            node = node.Parent
            self.PopulateViews(node)
            self.ReaderToGrid(self.conn_from_node(node).views())

    @eventhook
    def OnTableConstraints(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        a = self.conn_from_node(node).constraints(node.Text)
        self.DictListToGrid(a)
        i = 0
        for r in a:
            if r['TYPE'] == 'PRIMARY KEY':
                for j in range(len(r)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = PK_COLOR
            elif r['TYPE'] == 'FOREIGN KEY':
                for j in range(len(r)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = FK_COLOR
            elif r['TYPE'] == 'UNIQUE':
                for j in range(len(r)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = UK_COLOR
            i += 1
        self.dg_mode = 'TABLE_CONSTRAINTS'

    @eventhook
    def OnShowIndex(self, sender, args):
        node = self.select_node(sender, args, node_type='TABLE')
        conn = self.conn_from_node(node)
        a = conn.key_constraints_and_index(node.Text)
        self.DictListToGrid(a)
        i = 0
        for r in a:
            if r['CONST_TYPE'] == 'PRIMARY KEY':
                for j in range(len(r)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = PK_COLOR
            elif r['CONST_TYPE'] == 'FOREIGN KEY':
                for j in range(len(r)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = FK_COLOR
            elif r['CONST_TYPE'] == 'UNIQUE':
                for j in range(len(r)):
                    self._dg.Rows[i].Cells[j].Style.BackColor = UK_COLOR
            i += 1
        self.dg_mode = 'SHOW_INDEX'

    @eventhook
    def OnCreateGeneratorAndTrigger(self, sender, args, node_type='TABLE'):
        node = self.select_node(sender, args, node_type='TABLE')
        sql = fbutil.create_generator_and_trigger_sql(
            node.Text, self.conn_from_node(node).primary_keys(node.Text)[0], 1000000, 1)
        d = self.node_to_conndict(node.Parent.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateTable(node)

    @eventhook
    def OnTriggerActivate(self, sender, args):
        node = self.select_node(sender, args, node_type='TRIGGER')
        sql = 'alter trigger ' + node.Name + ' active'
        if self.ConfirmSql(self.conn_from_node(node), sql):
            while (node.Tag['NODE_TYPE'] != 'DATABASE'):
                node = node.Parent
            self.WalkAndUpdateTriggerNode(
                node, self.active_triggers(self.conn_from_node(node)))

    @eventhook
    def OnTriggerInactivate(self, sender, args):
        node = self.select_node(sender, args, node_type='TRIGGER')
        sql = 'alter trigger ' + node.Name + ' inactive'
        if self.ConfirmSql(self.conn_from_node(node), sql):
            while (node.Tag['NODE_TYPE'] != 'DATABASE'):
                node = node.Parent
            self.WalkAndUpdateTriggerNode(
                node, self.active_triggers(self.conn_from_node(node)))

    @eventhook
    def OnTriggerSource(self, sender, args):
        node = self.select_node(sender, args, node_type='TRIGGER')
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
        r = self.conn_from_node(node).trigger_source(node.Name)

        sql = 'set term !! ;\n'
        sql += 'alter trigger "' + node.Name + '"\n'
        sql += t_type[int(r['TRIGGER_TYPE'])]
        sql += ' position ' + str(r['SEQUENCE']) + '\n'
        sql += '\n'.join(r['SOURCE'].split('\n'))
        sql += '\n!!\nset term ; !!'
        while (node.Tag['NODE_TYPE'] != 'DATABASE'):
            node = node.Parent
        d = self.node_to_conndict(node)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            pass

    @eventhook
    def OnDropTrigger(self, sender, args):
        node = self.select_node(sender, args, node_type='TRIGGER')
        trigger_name = node.Name
        if self.ConfirmSql(
            self.conn_from_node(node),
            'drop trigger "' + trigger_name + '"'
        ):
            while (node.Tag['NODE_TYPE'] != 'DATABASE'):
                node = node.Parent
            self.WalkAndRemoveTriggerNode(node, trigger_name)

    @eventhook
    def OnCreateProcedure(self, sender, args):
        node = self.select_node(sender, args, node_type='PROCEDURES')
        d = self.node_to_conndict(node.Parent)
        sql = '''set term !!;
create procedure PROC_NAME
  (I_PARAM1 integer, I_PAREM2 VARCHAR(255))
  returns
  (O_PARAM1 integer, O_PARAM2 VARCHAR(255))
  as
  declare variable IVAL integer;
  declare variable DVAL date;
  begin
    /* write your code here */
    end!!

    set term ; !!
'''
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.PopulateProcedures(node)
            self.ReaderToGrid(self.conn_from_node(node).procedures())

    @eventhook
    def OnProcedureSource(self, sender, args):
        node = self.select_node(sender, args, node_type='PROCEDURE')
        proc = self.conn_from_node(node).procedure_source(node.Name)
        sql = 'set term !! ;\n'
        sql += 'alter procedure ' + proc['NAME'] + '('
        sql += ','.join(
            [in_p['NAME'] + ' ' + fbutil.fieldtype_to_string(in_p) for in_p in proc['IN_PARAMS']])
        sql += ')\nreturns ('
        sql += ','.join(
            [out_p['NAME'] + ' ' + fbutil.fieldtype_to_string(out_p) for out_p in proc['OUT_PARAMS']])
        sql += ') as\n' + '\n'.join(proc['SOURCE'].split('\n'))
        sql += '!!\nset term ; !!'
        d = self.node_to_conndict(node.Parent.Parent)
        dialog = FbSqlForm.FbSqlForm(d, self.user_pref, sql=sql)
        r = dialog.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self.ProcedureParamsToGrid(self.conn_from_node(node), node.Name)

    @eventhook
    def OnDropProcedure(self, sender, args):
        node = self.select_node(sender, args, node_type='PROCEDURE')
        if self.ConfirmSql(
            self.conn_from_node(node), "drop procedure " + node.Name
        ):
            node = node.Parent
            self.PopulateProcedures(node)
            self.ReaderToGrid(self.conn_from_node(node).procedures())

    @eventhook
    def OnCreateDB(self, sender, args):
        node = self.select_node(sender, args, node_type='SERVER')
        conn_d = None
        while True:
            dialog = dialogform.ConnPropForm(conn_d=conn_d)
            r = dialog.ShowDialog(self)
            if r == Forms.DialogResult.OK:
                conn_d = dialog.conn_d
                try:
                    d = {}
                    d.update(conn_d)
                    d['Server'] = node.Tag['SERVER']
                    db = fbutil.FbDatabase(d, create_flag=True)
                    db.open()
                    del d['Server']
                    d['NODE_TYPE'] = 'DATABASE'
                    img = self.imgidx('database')
                    node = Forms.TreeNode(conn_d['DISPLAY_NAME'], img, img)
                    self._tv.SelectedNode.Nodes.Add(node)
                    node.Tag = d
                    node.Tag['CONNECTION'] = db
                    self.PopulateDBItems(node)
                    break
                except Exception, e:
                    Forms.MessageBox.Show(str(e), "Can't create database")
            else:
                break

    @eventhook
    def OnQuit(self, sender, args):
        self.Close()

    @eventhook
    def OnClose(self, sender, args):
        self.user_pref['MAIN_WIDTH'] = self.ClientSize.Width
        self.user_pref['MAIN_HEIGHT'] = self.ClientSize.Height
        if self.menu['CONFIRM_SQL'].Checked:
            self.user_pref['CONFIRM_SQL'] = '1'
        else:
            self.user_pref['CONFIRM_SQL'] = '0'
        formutil.userpref_save(self.user_pref, USER_PROFILE)
        if (
            int(self.user_pref.get('MSSQL_SAVE_PASS_FLAG', '0')) == 0
            and 'MSSQL_Password' in self.user_pref
        ):
            del self.user_pref['MSSQL_Password']
        if (
            int(self.user_pref.get('ORACLE_SAVE_PASS_FLAG', '0')) == 0 and
            'ORACLE_Password' in self.user_pref
        ):
            del self.user_pref['ORACLE_Password']

        self.save_tree()

if (
    __name__ == '__main__' or
    (len(sys.argv[0]) >= 9 and sys.argv[0][-9:].lower() == 'fbconsole') or
    (len(sys.argv[0]) >= 13 and sys.argv[0][-13:].lower() == 'fbconsole.exe') or
    sys.argv[0] == ''
):
    if (not System.Threading.Mutex(False, APP_NAME).WaitOne(0, False)):
        sys.exit(0)

    for s in sys.argv[1:]:
        if s == '--init-tree':
            formutil.userpref_save({}, DBTREE_FILE)
        if s == '--init-pref':
            formutil.userpref_save({}, USER_PROFILE)
    if len(sys.argv) > 1:
        sys.exit(0)
    app = MainForm()
    Forms.Application.Run(app)

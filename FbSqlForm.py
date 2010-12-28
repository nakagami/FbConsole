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
import clr, sys
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Windows import Forms
from System.Drawing \
    import Font, FontStyle, GraphicsUnit, Point, Size, Image, Color
from System.IO import Path
from System.Text.RegularExpressions import Regex, RegexOptions
import dialogform
import formutil
import fbutil

sql_keywords = [
    'ABSOLUTE', 'ACTION', 'ACTIVE', 'ADD', 'ADMIN', 'AFTER',
    'ALL', 'ALLOCATE', 'ALTER', 'AND', 'ANY', 'ARE', 'AS',
    'ASC', 'ASCENDING', 'ASSERTION', 'AT', 'AUTHORIZATION',
    'AUTO', 'AUTODDL', 'AVG', 'BASED', 'BASENAME', 'BASE_NAME',
    'BEFORE', 'BEGIN', 'BETWEEN', 'BIT', 'BIT_LENGTH', 'BLOB',
    'BLOBEDIT', 'BOTH', 'BUFFER', 'BY', 'CACHE', 'CASCADE',
    'CASCADED', 'CASE', 'CAST', 'CATALOG', 'CHAR', 'CHARACTER',
    'CHAR_LENGTH', 'CHARACTER_LENGTH', 'CHECK', 'CHECK_POINT_LEN',
    'CHECK_POINT_LENGTH', 'CLOSE', 'COALESCE', 'COLLATE',
    'COLLATION', 'COLUMN', 'COMMIT', 'COMMITTED', 'COMPILETIME',
    'COMPUTED', 'CONDITIONAL', 'CONNECT', 'CONNECTION',
    'CONSTRAINT', 'CONSTRAINTS', 'CONTAINING', 'CONTINUE',
    'CONVERT', 'CORRESPONDING', 'COUNT', 'CREATE', 'CROSS',
    'CSTRING', 'CURRENT', 'CURRENT_DATE', 'CURRENT_TIME',
    'CURRENT_TIMESTAMP', 'CURRENT_USER', 'DATABASE', 'DATE',
    'DAY', 'DB_KEY', 'DEALLOCATE', 'DEBUG', 'DEC',
    'DECIMAL', 'DECLARE', 'DEFAULT', 'DEFERRABLE', 'DEFERRED',
    'DELETE', 'DESC', 'DESCENDING', 'DESCRIBE', 'DESCRIPTOR',
    'DIAGNOSTICS', 'DISCONNECT', 'DISPLAY', 'DISTINCT', 'DO',
    'DOMAIN', 'DOUBLE', 'DROP', 'ECHO', 'EDIT', 'ELSE', 'END',
    'END-EXEC', 'ENTRY_POINT', 'ESCAPE', 'EVENT', 'EXCEPT', 'EXCEPTION',
    'EXEC', 'EXECUTE', 'EXISTS', 'EXIT', 'EXTERN', 'EXTERNAL', 'EXTRACT',
    'FALSE', 'FETCH', 'FILE', 'FILTER', 'FIRST', 'FLOAT', 'FOR', 'FOREIGN',
    'FOUND', 'FREE_IT', 'FROM', 'FULL', 'FUNCTION', 'GDSCODE', 'GENERATOR',
    'GEN_ID', 'GET', 'GLOBAL', 'GO', 'GOTO', 'GRANT', 'GROUP',
    'GROUP_COMMIT_WAIT', 'GROUP_COMMIT_WAIT_TIME', 'HAVING', 'HELP',
    'HOUR', 'IDENTITY', 'IF', 'IMMEDIATE', 'IN', 'INACTIVE', 'INDEX',
    'INDICATOR', 'INIT', 'INITIALLY', 'INNER', 'INPUT', 'INPUT_TYPE',
    'INSENSITIVE', 'INSERT', 'INT', 'INTEGER', 'INTERSECT', 'INTERVAL',
    'INTO', 'IS', 'ISOLATION', 'ISQL', 'JOIN', 'KEY',
    'LANGUAGE', 'LAST', 'LC_MESSAGES', 'LC_TYPE', 'LEADING', 'LEFT',
    'LENGTH', 'LEV', 'LEVEL', 'LIKE', 'LOCAL', 'LOGFILE',
    'LOG_BUFFER_SIZE', 'LOG_BUF_SIZE', 'LONG', 'LOWER', 'MANUAL',
    'MATCH', 'MAX', 'MAXIMUM', 'MAXIMUM_SEGMENT', 'MAX_SEGMENT', 'MERGE',
    'MESSAGE', 'MIN', 'MINIMUM', 'MINUTE', 'MODULE', 'MODULE_NAME',
    'MONTH', 'NAMES', 'NATIONAL', 'NATURAL', 'NCHAR', 'NEXT',
    'NO', 'NOAUTO', 'NOT', 'NULL', 'NULLIF', 'NUM_LOG_BUFS',
    'NUM_LOG_BUFFERS', 'NUMERIC', 'OCTET_LENGTH', 'OF', 'ON', 'ONLY',
    'OPEN', 'OPTION', 'OR', 'ORDER', 'OUTER', 'OUTPUT', 'OUTPUT_TYPE',
    'OVERFLOW', 'OVERLAPS', 'PAD', 'PAGE', 'PAGELENGTH', 'PAGES',
    'PAGE_SIZE', 'PARAMETER', 'PARTIAL', 'PASSWORD', 'PLAN', 'POSITION',
    'POST_EVENT', 'PRECISION', 'PREPARE', 'PRESERVE', 'PRIMARY', 'PRIOR',
    'PRIVILEGES', 'PROCEDURE', 'PUBLIC', 'QUIT', 'RAW_PARTITIONS', 
    'RDB$DB_KEY', 'READ', 'REAL', 'RECORD_VERSION', 'REFERENCES', 
    'RELATIVE', 'RELEASE', 'RESERV', 'RESERVING', 'RESTRICT', 'RETAIN',
    'RETURN', 'RETURNING_VALUES', 'RETURNS', 'REVOKE', 'RIGHT', 'ROLE',
    'ROLLBACK', 'ROWS', 'RUNTIME', 'SCHEMA', 'SCROLL', 'SECOND',
    'SECTION', 'SELECT', 'SESSION', 'SESSION_USER', 'SET', 'SHADOW',
    'SHARED', 'SHELL', 'SHOW', 'SINGULAR', 'SIZE', 'SMALLINT', 'SNAPSHOT',
    'SOME', 'SORT', 'SPACE', 'SQL', 'SQLCODE', 'SQLERROR', 'SQLSTATE',
    'SQLWARNING', 'STABILITY', 'STARTING', 'STARTS', 'STATEMENT', 'STATIC',
    'STATISTICS', 'SUB_TYPE', 'SUBSTRING', 'SUM', 'SUSPEND', 'SYSTEM_USER',
    'TABLE', 'TEMPORARY', 'TERMINATOR', 'THEN', 'TIME', 'TIMESTAMP',
    'TIMEZONE_HOUR', 'TIMEZONE_MINUTE', 'TO', 'TRAILING', 'TRANSACTION',
    'TRANSLATE', 'TRANSLATION', 'TRIGGER', 'TRIM', 'TRUE',
    'TYPE', 'UNCOMMITTED', 'UNION', 'UNIQUE', 'UNKNOWN', 'UPDATE',
    'UPPER', 'USAGE', 'USER', 'USING', 'VALUE', 'VALUES',
    'VARCHAR', 'VARIABLE', 'VARYING', 'VERSION', 'VIEW', 'WAIT',
    'WEEKDAY', 'WHEN', 'WHENEVER', 'WHERE', 'WHILE', 'WITH',
    'WORK', 'WRITE', 'YEAR', 'YEARDAY', 'ZONE',
]


class FbSqlForm(Forms.Form):
    def __init__(self, conn_d, user_pref={}, sql=None):
        self.conn_d = conn_d
        self.executed = False
        self.user_pref = user_pref
        self.regex = Regex(
            r'''(\-\-.*?\n|\".*?\"|\'.*?\'|/\*(.|\n)*?\*/|\w+|\s+|.+?)''', 
            RegexOptions.IgnoreCase)
        self.tokens = []
        # MenuStrip & MenuItem
        menu = [
            ['EXEC', 'E&xcute', self.OnExec], 
            ['COPY', '&Copy', self.OnCopy], 
            ['PASTE', '&Paste', self.OnPaste], 
            ['SELECT_ALL', 'Select &All', self.OnSelectAll],
        ]

        self.SuspendLayout()
        self._tx = Forms.RichTextBox()
        self._tx.Font = Font(self._tx.Font.FontFamily, 10.5,
                                    FontStyle.Regular, GraphicsUnit.Point, 128)
        self._tx.Multiline = True
        self._tx.Dock = Forms.DockStyle.Fill
        self._tx.TabIndex = 2
        if sql:
            sql = '\r\n'.join(sql.strip().split('\n'))
            self._tx.Text = sql
        self.hilighter_all()
        self._tx.TextChanged += self.OnTextValueChanged

        self._dg = Forms.DataGridView()
        self._dg.ColumnHeadersHeightSizeMode = \
                    Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
        self._dg.AutoSizeColumnsMode = \
                    Forms.DataGridViewAutoSizeColumnsMode.AllCells
        self._dg.ColumnHeadersHeightSizeMode = \
                    Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
        self._dg.AutoSizeColumnsMode = \
                    Forms.DataGridViewAutoSizeColumnsMode.AllCells
        self._dg.AllowUserToAddRows = False
        self._dg.AllowUserToDeleteRows = False
        self._dg.EditMode = Forms.DataGridViewEditMode.EditProgrammatically
        self._dg.Dock = Forms.DockStyle.Fill
        self._dg.TabIndex = 3

        # SplitContainer
        self._split = Forms.SplitContainer()
        self._split.Dock = Forms.DockStyle.Fill
        self._split.Orientation = Forms.Orientation.Horizontal
        self._split.Panel1.Controls.Add(self._tx)
        self._split.Panel2.Controls.Add(self._dg)

        # ToolStripContainer
        self._tool = Forms.ToolStripContainer()
        self._tool.Dock = Forms.DockStyle.Fill
        toolStrip = Forms.ToolStrip()
        formutil.build_tool_strip(toolStrip, menu)
        self._tool.TopToolStripPanel.Controls.Add(toolStrip)
        self._tool.ContentPanel.Controls.Add(self._split)

        # Form
        self.Text = conn_d['DataSource'] + ':' + conn_d['Database']
        self.AutoScaleMode = Forms.AutoScaleMode.Font
        self.ClientSize = Size(self.user_pref.get('ISQL_WIDTH', 600),
                                    self.user_pref.get('ISQL_HEIGHT', 500))
        self.Controls.Add(self._tool)
        self.ResumeLayout(False)
        self.PerformLayout()
        self.Closed += self.OnClose


    def on_execute_batch(self, sender, args):
        if args.DataReader:
            formutil.ReaderToGrid(self._dg, args.DataReader)
        else:
            formutil.ClearGrid(self._dg, ['No Data'])

    def hilighter(self):
        all_tokens = []
        for m in self.regex.Matches(self._tx.Text):
            all_tokens.append([str(m), m.Index, m.Length])
        ts = all_tokens[:]

        # Get diff tokens to ts. Variable ts and self.tokens are broken.
        while len(ts) and len(self.tokens) and ts[0][0] == self.tokens[0][0]:
            del ts[0]
            del self.tokens[0]
        while len(ts) and len(self.tokens) and ts[-1][0] == self.tokens[-1][0]:
            del ts[-1]
            del self.tokens[-1]
        
        self.tokens = all_tokens    # Set current tokens.
        for t in ts:
            s = t[0]
            self._tx.Select(t[1], t[2])
            if s[:2] == '--' or (s[:2] == '/*' and s[-2:] == '*/'):
                self._tx.SelectionColor = Color.YellowGreen
            else:
                self._tx.SelectionColor = Color.Black

            if s.upper() in sql_keywords:
                f = FontStyle.Bold
            else:
                f = FontStyle.Regular
            self._tx.SelectionFont = Font(
                        self._tx.Font.FontFamily, self._tx.Font.Size, f)

    def hilighter_all(self):
        self._tx.Select(0, self._tx.Text.Length)
        self._tx.SelectionFont = Font(self._tx.Font.FontFamily, 
                        self._tx.Font.Size, FontStyle.Regular)
        self.hilighter()
        self._tx.Select(0, 0)

    def hilighter_current(self):
        i = self._tx.SelectionStart
        self.hilighter()
        self._tx.Select(i, 0)

    def OnTextValueChanged(self, sender, args):
        self.hilighter_current()

    def OnExec(self, sender, args):
        try:
            fbutil.FbDatabase(self.conn_d).execute_batch(
                                    self._tx.Text, self.on_execute_batch)
            self.executed = True
            self.DialogResult = Forms.DialogResult.OK
        except Exception, e:
            Forms.MessageBox.Show(str(e), "ISQL Error")

    def OnCopy(self, sender, args):
        Forms.Clipboard.SetDataObject(self._tx.Text)

    def OnPaste(self, sender, args):
        self._tx.Text = Forms.Clipboard.GetDataObject().GetData(
                                            Forms.DataFormats.StringFormat)
    def OnSelectAll(self, sender, args):
        self._tx.SelectAll()

    def OnClose(self, sender, args):
        self.user_pref['ISQL_WIDTH'] = self.ClientSize.Width
        self.user_pref['ISQL_HEIGHT'] = self.ClientSize.Height
    
if __name__ == '__main__':
    USER_PROFILE = 'FbSqlUserProf.cfg'
    try:
        conn_d = formutil.userpref_load(USER_PROFILE)
    except:
        conn_d = {
            'DataSource' : 'localhost',
            'Charset' : 'UNICODE_FSS', 
        }

    dialog = dialogform.ConnPropForm(conn_d=conn_d, require_server = True)
    r = dialog.ShowDialog()
    if r == Forms.DialogResult.OK:
        app = FbSqlForm(dialog.conn_d)
        Forms.Application.EnableVisualStyles()
        Forms.Application.Run(app)
        if not int(dialog.conn_d['SAVE_PASS_FLAG']):
            dialog.conn_d['Password'] = ''
        formutil.userpref_save(dialog.conn_d, USER_PROFILE)


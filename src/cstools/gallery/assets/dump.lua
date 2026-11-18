-- usage: CS=<colorscheme> PRE=<lua> OUT=<file> nvim --headless -u init.lua -l dump.lua
local groups = {
 "Normal","NormalFloat","FloatBorder","Comment","CursorLine","CursorLineNr","LineNr","Visual","Search","IncSearch","CurSearch",
 "StatusLine","StatusLineNC","Pmenu","PmenuSel","SignColumn","ColorColumn","MatchParen","NonText","WinSeparator","Folded","Title",
 "Keyword","Function","String","Type","Constant","Identifier","Statement","PreProc","Special","Number","Boolean","Operator","Delimiter","Todo","Error",
 "DiagnosticError","DiagnosticWarn","DiagnosticInfo","DiagnosticHint","DiagnosticOk",
 "DiagnosticVirtualTextError","DiagnosticVirtualTextWarn","DiagnosticVirtualTextInfo","DiagnosticVirtualTextHint",
 "DiagnosticUnderlineError","DiagnosticUnderlineWarn","DiagnosticUnderlineInfo","DiagnosticUnderlineHint",
 "DiffAdd","DiffChange","DiffDelete","DiffText","Added","Changed","Removed","GitSignsAdd","GitSignsChange","GitSignsDelete",
 "@variable","@variable.builtin","@variable.parameter","@variable.member","@constant","@constant.builtin","@constant.macro","@module","@label",
 "@string","@string.escape","@string.regexp","@string.special","@string.documentation","@character","@boolean","@number","@number.float",
 "@type","@type.builtin","@type.definition","@attribute","@property","@function","@function.builtin","@function.call","@function.macro",
 "@function.method","@function.method.call","@constructor","@operator","@keyword","@keyword.function","@keyword.operator","@keyword.import",
 "@keyword.type","@keyword.modifier","@keyword.repeat","@keyword.return","@keyword.exception","@keyword.conditional","@keyword.coroutine",
 "@punctuation.delimiter","@punctuation.bracket","@punctuation.special","@comment","@comment.documentation","@comment.todo","@comment.note",
 "@comment.warning","@comment.error","@tag","@tag.attribute","@tag.delimiter","@markup.heading","@diff.plus","@diff.minus","@diff.delta",
 "@lsp.type.parameter","@lsp.type.property","@lsp.type.namespace","@lsp.type.enumMember","@lsp.type.interface",
}
local cs, pre, out = os.getenv("CS"), os.getenv("PRE") or "", os.getenv("OUT")
if pre ~= "" then assert(load(pre))() end
local ok, err = pcall(vim.cmd.colorscheme, cs)
if not ok then io.stderr:write("ERR " .. cs .. ": " .. tostring(err) .. "\n"); os.exit(1) end
local function hex(n) return n and string.format("#%06x", n) or nil end
local res = { name = cs, background = vim.o.background, groups = {}, terminal = {} }
for _, g in ipairs(groups) do
  local h = vim.api.nvim_get_hl(0, { name = g, link = false })
  if next(h) then
    res.groups[g] = { fg = hex(h.fg), bg = hex(h.bg), sp = hex(h.sp), bold = h.bold, italic = h.italic, underline = h.underline, undercurl = h.undercurl, reverse = h.reverse, strikethrough = h.strikethrough }
  end
end
for i = 0, 15 do res.terminal[i + 1] = vim.g["terminal_color_" .. i] end
local f = assert(io.open(out, "w")); f:write(vim.json.encode(res)); f:close()

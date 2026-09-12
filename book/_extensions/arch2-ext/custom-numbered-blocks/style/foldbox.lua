local str = pandoc.utils.stringify
local pout = quarto.log.output

local function escapeHTML(value)
  return tostring(value or "")
    :gsub("&", "&amp;")
    :gsub("<", "&lt;")
    :gsub(">", "&gt;")
    :gsub('"', "&quot;")
end

-- Convert a 6-digit hex color string to R, G, B decimal values
-- e.g., "5B4B8A" -> 91, 75, 138
local function hexToRGB(hex)
  hex = hex:gsub("^#", "")
  local r = tonumber(hex:sub(1, 2), 16)
  local g = tonumber(hex:sub(3, 4), 16)
  local b = tonumber(hex:sub(5, 6), 16)
  return r, g, b
end


return {

defaultOptions={
  numbered = "true",
  boxstyle = "foldbox.simple",  -- Default to simple/compact style for all callouts
  collapse = "true",
  colors   = {"c0c0c0","808080"}
},

blockStart = function (tt, fmt)
  local Open =""
  local BoxStyle =" fbx-default closebutton"
  BoxStyle = " fbx-default closebutton"

  local texEnv = "fbx"
  if #tt.title > 0 then tt.typlabelTag = tt.typlabelTag..":" end
  if fmt =="html" then
    local isEpub = quarto.doc.is_format("epub")
    local label = escapeHTML(tt.typlabelTag)
    local title = escapeHTML(tt.title)
    local titleSep = ""
    if #tt.title > 0 then titleSep = "\u{2003}" end

    -- EPUB readers do not consistently support interactive disclosure widgets.
    -- Emit static, balanced XHTML instead of HTML <details>/<summary> markup.
    if isEpub then
      return '<div class="'..tt.type..BoxStyle..' fbx-epub" style="border: 1px solid #7c929c; border-left: 0.3rem solid #1f5f7a; margin: 1em 0;">'..
        '<div class="fbx-epub-summary" style="background: #eef4f6; padding: 0.65em 0.8em;"><strong>'..label..titleSep..title..'</strong></div>'..
        '<div class="fbx-epub-body" style="padding: 0.1em 0.8em 0.7em;">'
    end

    if tt.collapse =="false" then
      Open=" open"
    end
    if tt.boxstyle =="foldbox.simple"
      then
        BoxStyle=" fbx-simplebox fbx-default"
    --    Open=" open" do not force override. Chose this in yaml or individually.
    --    we would want e.g to have remarks closed by default
      end
    result = ('<details class=\"'..tt.type..BoxStyle ..'\"'..Open..'><summary>'..'<strong>'..label..titleSep..title..'</strong></summary><div>')
    return result

  elseif fmt =="tex" then
    if tt.boxstyle=="foldbox.simple" then texEnv = "fbxSimple" end
    return('\\Needspace{8\\baselineskip}\n'..
           '\\begin{'..texEnv..'}{'..tt.type..'}{'..tt.typlabelTag..'}{'..tt.title..'}\n'..
           '\\phantomsection\\label{'..tt.id..'}\n')
  else
    return("")
  end
end,

blockEnd = function (tt, fmt)
  local texEnv = "fbx"
  if fmt =="html" then
    if quarto.doc.is_format("epub") then
      return('</div></div>')
    end
    return('</div></details>')
  elseif fmt =="tex" then
    if tt.boxstyle=="foldbox.simple" then texEnv = "fbxSimple" end
     return('\\end{'..texEnv..'}\n')
  else return ('ende mit format '..fmt..'=================')
  end
end,

insertPreamble = function(doc, classDefs, fmt)
  local ishtml = quarto.doc.is_format("html")
  local ispdf = quarto.doc.is_format("pdf")
  local isepub = quarto.doc.is_format("epub")
  -- Note: ePub format is treated as HTML (fmt="html") since ePub uses HTML internally
  local StyleCSSTeX = {}

  -- Set icon path from filter-metadata configuration if available
  local meta = doc.meta
  local filterMetadata = meta["filter-metadata"]
  local iconCSS = ""
  if filterMetadata and filterMetadata["arch2-ext/custom-numbered-blocks"] then
    local config = filterMetadata["arch2-ext/custom-numbered-blocks"]
    if config["icon-path"] then
      local iconPath = str(config["icon-path"])
      -- Per-target icon format: HTML/EPUB use vector SVG; the LaTeX/PDF build
      -- uses PDF (pdflatex cannot embed SVG). icon-format is the PDF format;
      -- icon-format-html overrides the web format (defaults to svg).
      local iconFormat = str(config["icon-format"] or "pdf")
      local iconFormatHtml = str(config["icon-format-html"] or "svg")

      if fmt == "html" then
        -- Generate dynamic CSS for icon paths - generic version using classDefs
        iconCSS = "<style>\n"
        if classDefs then
          for calloutType, _ in pairs(classDefs) do
            -- Convert hyphens to underscores for icon filename.
            local iconFileName = calloutType:gsub("-", "_")
            iconCSS = iconCSS .. "details." .. calloutType .. " > summary::before {\n"
            iconCSS = iconCSS .. "  background-image: url(\"" .. iconPath .. "/icon_" .. iconFileName .. "." .. iconFormatHtml .. "\");\n"
            iconCSS = iconCSS .. "}\n"
          end
        end
        iconCSS = iconCSS .. "</style>"
      elseif fmt == "pdf" then
        -- Define the commands before including foldbox.tex
        quarto.doc.include_text("in-header", "\\newcommand{\\fbxIconPath}{" .. iconPath .. "}")
        quarto.doc.include_text("in-header", "\\newcommand{\\fbxIconFormat}{" .. iconFormat .. "}")
      end
    end
  end

  -- =========================================================================
  -- Generate CSS/LaTeX color styles from YAML configuration
  -- YAML is the single source of truth for all callout colors.
  -- colors[1] = background hex (e.g., "F0F0F8")
  -- colors[2] = border/accent hex (e.g., "5B4B8A")
  -- =========================================================================

  -- Light mode opacity for background/title (subtle tint)
  local LIGHT_BG_OPACITY = 0.06
  -- Dark mode opacity (stronger tint for visibility on dark backgrounds)
  local DARK_BG_OPACITY = 0.12

  local extractStyleFromMeta = function (fmt)
    local result
    if classDefs ~= nil then
      for cls, options in pairs(classDefs) do
        if options.colors then
          if fmt == "html" then
            -- Keep legacy --color1/--color2 for any CSS that still references them
            table.insert(StyleCSSTeX, "."..cls.." {\n")
            for i, col in ipairs(options.colors) do
              table.insert(StyleCSSTeX, "  --color"..i..": #"..col..";\n")
            end
            -- Generate semantic color variables from color2 (the accent/border color)
            -- Light mode values are used directly; dark mode values are stored
            -- as --dark-* for dark-mode.scss to reference via the manual toggle.
            if options.colors[2] then
              local borderHex = options.colors[2]
              local r, g, b = hexToRGB(borderHex)
              table.insert(StyleCSSTeX, "  --border-color: #"..borderHex..";\n")
              table.insert(StyleCSSTeX, "  --background-color: rgba("..r..", "..g..", "..b..", "..LIGHT_BG_OPACITY..");\n")
              table.insert(StyleCSSTeX, "  --title-background-color: rgba("..r..", "..g..", "..b..", "..LIGHT_BG_OPACITY..");\n")
              -- Pre-computed dark mode values for manual toggle (dark-mode.scss)
              table.insert(StyleCSSTeX, "  --dark-background-color: rgba("..r..", "..g..", "..b..", "..DARK_BG_OPACITY..");\n")
              table.insert(StyleCSSTeX, "  --dark-title-background-color: rgba("..r..", "..g..", "..b..", "..DARK_BG_OPACITY..");\n")
            end
            table.insert(StyleCSSTeX, "}\n")
          elseif fmt == "pdf" then
            for i, col in ipairs(options.colors) do
              table.insert(StyleCSSTeX, "\\definecolor{"..cls.."-color"..i.."}{HTML}{"..col.."}\n")
            end
          end
        end
      end
    end
    result = pandoc.utils.stringify(StyleCSSTeX)
    if fmt == "html" then result = "<style>\n"..result.."</style>" end
    if fmt == "pdf" then result="%%==== colors from yaml ===%\n"..result.."%=============%\n" end
    return(result)
  end

  -- Generate dark mode CSS overrides from YAML colors.
  -- Emits two parallel rule-sets so dark styling works regardless of how dark
  -- mode is activated:
  --   1. @media (prefers-color-scheme: dark) -- OS-level system preference
  --   2. body.quarto-dark selector          -- Quarto's manual toggle button
  local generateDarkModeCSS = function ()
    local darkCSS = {}
    if classDefs == nil then return "" end

    -- Helper: emit per-callout rules for one selector context
    local function emitCalloutRules(prefix)
      for cls, options in pairs(classDefs) do
        if options.colors and options.colors[2] then
          local borderHex = options.colors[2]
          local r, g, b = hexToRGB(borderHex)
          table.insert(darkCSS, prefix.."details."..cls.." {\n")
          table.insert(darkCSS, "    --text-color: #e6e6e6;\n")
          table.insert(darkCSS, "    --background-color: rgba("..r..", "..g..", "..b..", "..DARK_BG_OPACITY..");\n")
          table.insert(darkCSS, "    --title-background-color: rgba("..r..", "..g..", "..b..", "..DARK_BG_OPACITY..");\n")
          table.insert(darkCSS, "    border-color: #"..borderHex..";\n")
          table.insert(darkCSS, "  }\n")
          table.insert(darkCSS, prefix.."details."..cls.." summary,\n")
          table.insert(darkCSS, prefix.."details."..cls.." summary strong,\n")
          table.insert(darkCSS, prefix.."details."..cls.." > summary {\n")
          table.insert(darkCSS, "    color: #f0f0f0 !important;\n")
          table.insert(darkCSS, "  }\n")
          table.insert(darkCSS, prefix.."details."..cls.." code {\n")
          table.insert(darkCSS, "    color: #e6e6e6 !important;\n")
          table.insert(darkCSS, "  }\n")
        end
      end
    end

    -- 1. OS-level dark mode via @media query
    table.insert(darkCSS, "<style>\n@media (prefers-color-scheme: dark) {\n")
    emitCalloutRules("  ")
    table.insert(darkCSS, "}\n")

    -- 2. Quarto manual toggle button via body.quarto-dark class
    emitCalloutRules("body.quarto-dark ")
    table.insert(darkCSS, "</style>\n")

    return pandoc.utils.stringify(darkCSS)
  end

  local preamblestuff = extractStyleFromMeta(fmt)
  local darkModeCSSBlock = ""
  if fmt == "html" and not isepub then
    darkModeCSSBlock = generateDarkModeCSS()
  end

  if fmt == "html"
  then
    quarto.doc.add_html_dependency({
      name = 'foldbox',
      stylesheets = {'style/foldbox.css'}
    })
   elseif fmt == "pdf"
    then
      quarto.doc.use_latex_package("needspace")
      quarto.doc.use_latex_package("tcolorbox","many")
      quarto.doc.include_file("in-header", 'style/foldbox.tex')
  end
  if preamblestuff then quarto.doc.include_text("in-header", preamblestuff) end
  if darkModeCSSBlock ~= "" then quarto.doc.include_text("in-header", darkModeCSSBlock) end
  if iconCSS ~= "" then quarto.doc.include_text("in-header", iconCSS) end
  return(doc)
end
}

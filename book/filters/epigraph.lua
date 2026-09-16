function Div(el)
  if el.classes:includes('epigraph') and FORMAT:match('latex') then
    local new_blocks = { pandoc.RawBlock('latex', '\\begin{epigraph}') }
    for _, block in ipairs(el.content) do
      if block.t == 'BlockQuote' then
        local bq_blocks = block.content
        if #bq_blocks >= 2 then
          table.insert(new_blocks, pandoc.RawBlock('latex', '\\begin{epigraphtext}'))
          for i = 1, #bq_blocks - 1 do
            table.insert(new_blocks, bq_blocks[i])
          end
          table.insert(new_blocks, pandoc.RawBlock('latex', '\\end{epigraphtext}'))
          table.insert(new_blocks, pandoc.RawBlock('latex', '\\begin{epigraphsource}'))
          table.insert(new_blocks, bq_blocks[#bq_blocks])
          table.insert(new_blocks, pandoc.RawBlock('latex', '\\end{epigraphsource}'))
        else
          table.insert(new_blocks, pandoc.RawBlock('latex', '\\begin{epigraphtext}'))
          for _, b in ipairs(bq_blocks) do
            table.insert(new_blocks, b)
          end
          table.insert(new_blocks, pandoc.RawBlock('latex', '\\end{epigraphtext}'))
        end
      else
        table.insert(new_blocks, block)
      end
    end
    table.insert(new_blocks, pandoc.RawBlock('latex', '\\end{epigraph}'))
    return new_blocks
  end
end

-- Pin chapter cover maps inline in LaTeX so Section X.1 stays on Page 2 with the map
-- and does not leak onto the chapter opener (Page 1).
function Figure(el)
  if FORMAT:match('latex') and el.identifier and el.identifier:match('cover%-map') then
    el.attributes['fig-pos'] = 'H'
    return el
  end
end

function FloatRefTarget(el)
  if FORMAT:match('latex') and el.identifier and el.identifier:match('cover%-map') then
    el.attributes['fig-pos'] = 'H'
    return el
  end
end

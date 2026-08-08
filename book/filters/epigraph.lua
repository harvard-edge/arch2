function Div(el)
  if el.classes:includes('epigraph') then
    if FORMAT:match 'latex' then
      table.insert(el.content, 1, pandoc.RawBlock('latex', '\\begin{epigraph}'))
      table.insert(el.content, pandoc.RawBlock('latex', '\\end{epigraph}'))
      return el
    end
  end
end

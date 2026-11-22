export function filterFluxGuides(guides,query) {
  const terms=query.toLowerCase().trim().split(/\s+/);
  return guides.filter(item=>terms.every(term=>
    [item.id,item.label,item.roof,item.entrance,item.version,item.source,item.role].join(' ').toLowerCase().includes(term)));
}

export function addFluxRolePrompt(prompt,rolePrompt) {
  return prompt.includes(rolePrompt) ? prompt : [prompt.trim(),rolePrompt].filter(Boolean).join(' ');
}

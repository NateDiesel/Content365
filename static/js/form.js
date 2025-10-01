(function(){
  const pills = Array.from(document.querySelectorAll('.pill'));
  const field = document.getElementById('platformsField');
  const selectAll = document.getElementById('selectAll');

  // Default select Instagram + LinkedIn
  const defaultSet = new Set((field.value || '').split(',').map(s => s.trim()).filter(Boolean));

  function syncFromField(){
    const current = new Set((field.value || '').split(',').map(s => s.trim()).filter(Boolean));
    pills.forEach(p => {
      const v = p.getAttribute('data-value');
      p.classList.toggle('selected', current.has(v));
    });
  }
  function syncToField(){
    const selected = pills.filter(p => p.classList.contains('selected')).map(p => p.getAttribute('data-value'));
    field.value = selected.join(',');
  }

  pills.forEach(p => {
    const v = p.getAttribute('data-value');
    if(defaultSet.has(v)) p.classList.add('selected');
    p.addEventListener('click', () => {
      p.classList.toggle('selected');
      syncToField();
    });
  });

  selectAll.addEventListener('click', (e) => {
    e.preventDefault();
    const allSelected = pills.every(p => p.classList.contains('selected'));
    pills.forEach(p => p.classList.toggle('selected', !allSelected));
    syncToField();
  });

  // Init
  syncFromField();
})();
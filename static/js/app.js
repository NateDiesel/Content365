document.addEventListener('click', function(e){
  const t = e.target.closest('.pill');
  if(!t) return;
  t.classList.toggle('selected');
  const container = document.getElementById('platforms-hidden');
  if(!container) return;
  container.innerHTML = '';
  const vals = Array.from(document.querySelectorAll('.pill.selected')).map(x=>x.dataset.value);
  vals.forEach(v => {
    const inp = document.createElement('input');
    inp.type = 'hidden';
    inp.name = 'platforms';
    inp.value = v;
    container.appendChild(inp);
  });
});
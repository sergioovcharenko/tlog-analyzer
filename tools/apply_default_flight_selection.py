from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')

helper = r'''
  function selectDefaultFlightIndex(flights){
    if(!Array.isArray(flights) || !flights.length) return 0;
    var bestIndex=0;
    var bestScore=-1;
    var bestRows=-1;
    flights.forEach(function(flight,index){
      var points=Array.isArray(flight&&flight.points)?flight.points:[];
      var rows=Array.isArray(flight&&flight.rows)?flight.rows:[];
      var score=points.length;
      if(score>bestScore || (score===bestScore && rows.length>bestRows)){
        bestIndex=index;
        bestScore=score;
        bestRows=rows.length;
      }
    });
    return bestIndex;
  }

'''

marker = '  function renderMap(data){\n'
if 'function selectDefaultFlightIndex(flights)' not in text:
    if marker not in text:
        raise SystemExit('renderMap marker not found')
    text = text.replace(marker, helper + marker, 1)

render_start = text.index('  function renderMap(data){')
active_pos = text.index('    STATE.active=0;', render_start)
text = text[:active_pos] + '    STATE.active=selectDefaultFlightIndex(STATE.flights);' + text[active_pos + len('    STATE.active=0;'):]

path.write_text(text, encoding='utf-8')

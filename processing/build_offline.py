import re,sys
old=open('out/Analog-Finder-map-offline.html').read()
new=open(sys.argv[1]).read()
fonts=re.search(r'<style>\s*(@font-face.*?)</style>',old,re.S).group(1)
assert fonts.count('@font-face')>=5
d3=open('vendor2/d3-7.8.5/package/dist/d3.min.js').read() if __import__('os').path.exists('vendor2/d3-7.8.5/package/dist/d3.min.js') else None
tj=open('vendor2/topojson-3.0.2/package/dist/topojson.min.js').read() if __import__('os').path.exists('vendor2/topojson-3.0.2/package/dist/topojson.min.js') else None
assert d3 and tj
new=re.sub(r'<link rel="preconnect"[^>]*>\s*','',new)
new=re.sub(r'<link href="https://fonts.googleapis.com[^>]*>','<style>'+fonts+'</style>',new)
new=new.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>','<script>'+d3.replace('</script','<\\/script')+'</script>')
new=new.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>','<script>'+tj.replace('</script','<\\/script')+'</script>')
assert 'cdnjs' not in new and 'googleapis' not in new, [m for m in re.findall(r'https://[^"\' ]+',new) if 'cdnjs' in m or 'google' in m][:5]
open(sys.argv[2],'w').write(new); print(len(new))

import argparse, hashlib, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]; BANK=ROOT/'content/scripts.json'; HISTORY=ROOT/'data/history.json'
def cmd(args):
 p=subprocess.run(args,capture_output=True,text=True)
 if p.returncode: raise RuntimeError(f"{args[0]} failed: {p.stderr[-2000:]}")
 return p.stdout.strip()
def hist_read(): return json.loads(HISTORY.read_text()) if HISTORY.exists() else {'videos':[]}
def select(day,hist):
 bank=json.loads(BANK.read_text(encoding='utf-8')); used={x.get('script_id') for x in hist['videos'] if x.get('date')==day}
 start=datetime.strptime(day,'%Y-%m-%d').timetuple().tm_yday%len(bank)
 for i in range(len(bank)):
  x=bank[(start+i)%len(bank)]
  if x['id'] not in used:return x
 raise RuntimeError('All scripts used today; add more original scripts or retry tomorrow.')
def fnt(n,b=False):
 p='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if b else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
 return ImageFont.truetype(p,n) if Path(p).exists() else ImageFont.load_default()
def wrap(d,s,f,w):
 lines=[]; cur=''
 for word in s.split():
  test=(cur+' '+word).strip()
  if d.textbbox((0,0),test,font=f)[2]<=w:cur=test
  else:
   if cur:lines.append(cur)
   cur=word
 if cur:lines.append(cur)
 return lines
def card(item,caption,i,total,path):
 im=Image.new('RGB',(1080,1920),(13,20,43));d=ImageDraw.Draw(im)
 for y in range(1920):
  t=y/1920;d.line((0,y,1080,y),fill=(int(13+16*t),int(20+8*t),int(43+36*t)))
 d.ellipse((650,150,1120,620),outline=(70,91,145),width=5);d.rounded_rectangle((70,80,1010,1830),radius=42,outline=(75,91,135),width=3)
 d.text((120,145),'STOIC MINDSET / DAILY PRACTICE',font=fnt(28,1),fill=(165,185,235));d.text((120,280),f'{i+1:02d} / {total:02d}',font=fnt(32,1),fill=(235,190,110))
 y=430
 for line in wrap(d,item['title'].upper(),fnt(64,1),820)[:3]:d.text((120,y),line,font=fnt(64,1),fill=(248,249,252));y+=88
 d.line((120,y+30,360,y+30),fill=(231,181,91),width=8);y+=145
 for line in wrap(d,caption,fnt(52,1),820)[:5]:d.text((120,y),line,font=fnt(52,1),fill=(220,228,245));y+=76
 d.text((120,1650),'PAUSE • THINK • CHOOSE',font=fnt(30,1),fill=(235,190,110));d.text((120,1720),'Original Hinglish Stoic reflections',font=fnt(24),fill=(150,166,203));im.save(path)
def build(item,out):
 for tool in ['ffmpeg','ffprobe','espeak-ng']:
  if not shutil.which(tool):raise RuntimeError('Missing dependency: '+tool)
 out=Path(out);work=out/'work';work.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
 voices=cmd(['espeak-ng','--voices']);voice='en-in' if 'en-in' in voices else 'en';audio=work/'voice.wav'
 cmd(['espeak-ng','-v',voice,'-s','145','-w',str(audio),item['narration']])
 seconds=float(cmd(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(audio)]))
 if not 30<=seconds<=60:raise RuntimeError(f'Narration is {seconds:.1f}s; target is 30–60s. Adjust script.')
 cards=[]
 for i,s in enumerate(item['scenes']):
  p=work/f'scene-{i:02d}.png';card(item,s,i,len(item['scenes']),p);cards.append(p)
 per=seconds/len(cards);lst=work/'slides.txt';lst.write_text(''.join(f"file '{p.resolve()}'\nduration {per:.5f}\n" for p in cards)+f"file '{cards[-1].resolve()}'\n")
 video=out/'short.mp4'
 cmd(['ffmpeg','-y','-f','concat','-safe','0','-i',str(lst),'-i',str(audio),'-vf','fps=30,format=yuv420p,scale=1080:1920','-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(video)])
 shutil.copy2(cards[0],out/'thumbnail.png');(out/'script.txt').write_text(item['narration']+'\n\nSource: '+item['source']+'\n')
 meta={'title':item['title']+' | Stoic Wisdom #shorts','description':item['hook']+'\n\nOriginal Hinglish reflection inspired by: '+item['source']+'\n\n#stoicism #selfdiscipline #wisdom #shorts','tags':['stoicism','stoic philosophy','self discipline','hinglish','shorts'],'categoryId':'22','defaultLanguage':'hi'}
 (out/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
 p=json.loads(cmd(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]));v=next((s for s in p['streams'] if s['codec_type']=='video'),None);a=next((s for s in p['streams'] if s['codec_type']=='audio'),None)
 if not v or not a or (v['width'],v['height'])!=(1080,1920):raise RuntimeError('Video/audio stream or portrait dimensions invalid')
 dur=float(p['format']['duration'])
 if not 30<=dur<=60 or abs(dur-seconds)>2:raise RuntimeError(f'Render duration invalid: {dur:.1f}s')
 return video,meta,{'duration_seconds':round(dur,2),'width':1080,'height':1920,'video_codec':v['codec_name'],'audio_codec':a['codec_name']}
def upload(video,meta):
 from google.auth.transport.requests import Request
 from google.oauth2.credentials import Credentials
 from googleapiclient.discovery import build
 from googleapiclient.http import MediaFileUpload
 c=Credentials(None,refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],token_uri='https://oauth2.googleapis.com/token',client_id=os.environ['YOUTUBE_CLIENT_ID'],client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],scopes=['https://www.googleapis.com/auth/youtube.upload'])
 c.refresh(Request());yt=build('youtube','v3',credentials=c,cache_discovery=False)
 body={'snippet':{'title':meta['title'][:100],'description':meta['description'],'tags':meta['tags'],'categoryId':'22','defaultLanguage':'hi'},'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}}
 return yt.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(video),mimetype='video/mp4',resumable=True)).execute()['id']
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',default='output');p.add_argument('--date',default=datetime.now().astimezone().strftime('%Y-%m-%d'));p.add_argument('--upload',action='store_true');a=p.parse_args(argv)
 h=hist_read();item=select(a.date,h);digest=hashlib.sha256(item['narration'].encode()).hexdigest()
 if any(x.get('date')==a.date and x.get('content_hash')==digest for x in h['videos']):raise RuntimeError('Duplicate content already processed today.')
 video,meta,check=build(item,a.output);vid=upload(video,meta) if a.upload else None
 h['videos'].append({'date':a.date,'script_id':item['id'],'content_hash':digest,'youtube_video_id':vid,'privacy_status':'private' if vid else 'not_uploaded','validation':check,'created_at_utc':datetime.now(timezone.utc).isoformat()})
 HISTORY.parent.mkdir(parents=True,exist_ok=True);HISTORY.write_text(json.dumps(h,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'script_id':item['id'],'youtube_video_id':vid,'validation':check}));return 0
if __name__=='__main__':raise SystemExit(main())

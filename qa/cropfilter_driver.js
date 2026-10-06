/* qa/cropfilter_driver.js — filter quality probe for qa_cropfilter.py.
   Synthetic text pages (clean + heavy side shadow) through CV.applyFilter.
   Prints one JSON object per line: {name, pass, detail}. */
const fs=require('fs');
global.window={};
const HUB=__dirname+'/..';
let src=fs.readFileSync(HUB+'/js/scan.js','utf8');
const m=src.match(/var CV=\(function\(\)\{[\s\S]*?\n\}\)\(\);/);
if(!m){ console.log(JSON.stringify({name:'driver',pass:false,detail:'CV block not found'})); process.exit(0); }
eval(m[0].replace('var CV=','globalThis.CV='));
const CV=globalThis.CV;

const W=600,H=800;
let seed=12345; function rnd(){ seed=(seed*1103515245+12345)&0x7fffffff; return seed/0x7fffffff; }
function makePage(shadow){
  const px=new Uint8ClampedArray(W*H*4);
  const bg=[], tx=[];
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){
    let g=228-18*(y/H)+(rnd()-0.5)*14;
    if(shadow) g*=(0.55+0.45*(x/W));
    const o=(y*W+x)*4;
    px[o]=g+6; px[o+1]=g; px[o+2]=g-10; px[o+3]=255;
    if(x>40&&x<W-40&&((y>60&&y<120)||(y>200&&y<260)||(y>420&&y<480)||(y>600&&y<660))) bg.push(o);
  }
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){
    const inLine=(y>130&&y<190)||(y>270&&y<330)||(y>490&&y<550)||(y>670&&y<730);
    if(inLine&&x>60&&x<W-60&&((x+y)%9<6)){
      const o=(y*W+x)*4, v=26+rnd()*20;
      px[o]=v; px[o+1]=v; px[o+2]=v; tx.push(o);
    }
  }
  return {px,bg,tx};
}
function meanLum(d,z){ let s=0; for(const o of z) s+=(d[o]+d[o+1]+d[o+2])/3; return s/z.length; }
function fracBlack(d,z,thr){ let c=0; for(const o of z) if((d[o]+d[o+1]+d[o+2])/3<thr) c++; return c/z.length; }
for(const shadow of [false,true]){
  const {px,bg,tx}=makePage(shadow);
  const tag=shadow?'shadow':'clean';
  for(const f of ['bw','magic']){
    const out=CV.applyFilter(px,W,H,f);
    const b=meanLum(out,bg), t=meanLum(out,tx), sp=fracBlack(out,bg,128);
    const pass=b>200&&t<110&&sp<0.02;
    console.log(JSON.stringify({name:'filter '+f+' ('+tag+')',pass,
      detail:'bgMean='+b.toFixed(1)+' textMean='+t.toFixed(1)+' bgBlackFrac='+sp.toFixed(4)}));
  }
}

/* ============================================================
   Student Scanner — 100% offline document scanner + file studio
   Original code by the Onaro team. Third-party libraries used
   under license only (all vendored, zero network at runtime):
   pdf-lib, pdf.js, mammoth, docx, heic2any, SheetJS.
   ============================================================ */
(function(){
'use strict';
var HUB=window.HUB||{};
var ui=HUB.ui||{};
function scIcon(n){ return (HUB.icons&&HUB.icons.icon)?HUB.icons.icon(n||'scan-doc'):'\uD83D\uDCC4'; }
var t=function(k,v){ return (HUB.i18n&&HUB.i18n.t)?HUB.i18n.t(k,v):k; };
var esc=function(s){ return ui.esc?ui.esc(String(s==null?'':s)):String(s==null?'':s); };
function $(sel,root){ return (root||document).querySelector(sel); }
function el(html){ var d=document.createElement('div'); d.innerHTML=html; return d.firstChild; }

/* ---------------- IndexedDB: hub_scan_v1 (on-device only) ---------------- */
var DB=(function(){
  var db=null, NAME='hub_scan_v1';
  function open(){
    if(db) return Promise.resolve(db);
    return new Promise(function(res,rej){
      var rq=indexedDB.open(NAME,1);
      rq.onupgradeneeded=function(){ rq.result.createObjectStore('files',{keyPath:'id',autoIncrement:true}); };
      rq.onsuccess=function(){ db=rq.result; res(db); };
      rq.onerror=function(){ rej(rq.error); };
    });
  }
  function tx(mode,fn){
    return open().then(function(d){
      return new Promise(function(res,rej){
        var tr=d.transaction('files',mode), st=tr.objectStore('files'), out=null;
        try{ out=fn(st); }catch(e){ rej(e); return; }
        tr.oncomplete=function(){ res(out&&'result' in out?out.result:null); };
        tr.onerror=function(){ rej(tr.error); };
      });
    });
  }
  return {
    add:function(rec){ return tx('readwrite',function(st){ return st.add(rec); }); },
    all:function(){ return tx('readonly',function(st){ return st.getAll(); }); },
    del:function(id){ return tx('readwrite',function(st){ st.delete(id); return null; }); }
  };
})();
var fileCount=0;
function refreshCount(){
  DB.all().then(function(a){
    fileCount=(a||[]).length;
    var c=$('[data-scan-card] .sc-count'); if(c) c.textContent=fileCount;
  }).catch(function(){});
}

/* ---------------- file helpers ---------------- */
function fileBytes(file){
  return new Promise(function(res,rej){
    var fr=new FileReader();
    fr.onload=function(){ res(new Uint8Array(fr.result)); };
    fr.onerror=function(){ rej(fr.error); };
    fr.readAsArrayBuffer(file);
  });
}
function blobOf(bytes,mime){ return new Blob([bytes],{type:mime||'application/octet-stream'}); }
function downloadBlob(blob,filename){
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob); a.download=filename||'file';
  document.body.appendChild(a); a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); },4000);
}
/* system share sheet first (like most apps), download fallback */
function shareOrDownload(blob,filename,title){
  var file=null;
  try{ file=new File([blob],filename,{type:blob.type}); }catch(e){}
  if(file&&navigator.canShare&&navigator.canShare({files:[file]})){
    return navigator.share({files:[file],title:title||filename}).catch(function(){ downloadBlob(blob,filename); });
  }
  downloadBlob(blob,filename);
  return Promise.resolve();
}
function loadImage(bytes){
  return new Promise(function(res,rej){
    var url=URL.createObjectURL(blobOf(bytes));
    var img=new Image();
    img.onload=function(){ URL.revokeObjectURL(url); res(img); };
    img.onerror=function(){ URL.revokeObjectURL(url); rej(new Error('img')); };
    img.src=url;
  });
}
function imgToCanvas(img,maxSide){
  /* Tiered: try the requested size, halve on allocation failure. Never throws
     away the user's image with a silent tiny output. */
  var target=maxSide||1600, nw=img.naturalWidth||1, nh=img.naturalHeight||1;
  for(var a=0;a<3;a++){
    var s=Math.min(1,target/Math.max(nw,nh));
    try{
      var cv=document.createElement('canvas');
      cv.width=Math.max(1,Math.round(nw*s)); cv.height=Math.max(1,Math.round(nh*s));
      cv.getContext('2d').drawImage(img,0,0,cv.width,cv.height);
      return cv;
    }catch(e){ target=Math.round(target/2); }
  }
  var cv2=document.createElement('canvas');
  cv2.width=320; cv2.height=Math.max(1,Math.round(320*nh/nw));
  cv2.getContext('2d').drawImage(img,0,0,cv2.width,cv2.height);
  return cv2;
}
function canvasJpg(cv,q){
  return new Promise(function(res,rej){
    cv.toBlob(function(b){
      if(!b){ rej(new Error('jpg')); return; }
      var fr=new FileReader();
      fr.onload=function(){ res(new Uint8Array(fr.result)); };
      fr.onerror=function(){ rej(fr.error); };
      fr.readAsArrayBuffer(b);
    },'image/jpeg',q||0.92);
  });
}
function canvasPng(cv){
  return new Promise(function(res,rej){
    cv.toBlob(function(b){
      if(!b){ rej(new Error('png')); return; }
      var fr=new FileReader();
      fr.onload=function(){ res(new Uint8Array(fr.result)); };
      fr.onerror=function(){ rej(fr.error); };
      fr.readAsArrayBuffer(b);
    },'image/png');
  });
}

/* ---------------- vendor lazy loader (zero network: local files only) ---------------- */
var VENDOR={
  'pdf-lib':{src:'vendor/pdf-lib.min.js',test:function(){ return window.PDFLib; }},
  'pdfjs':{src:'vendor/pdfjs.min.js',test:function(){ return window.pdfjsLib; }},
  'mammoth':{src:'vendor/mammoth.browser.min.js',test:function(){ return window.mammoth; }},
  'docx':{src:'vendor/docx.umd.js',test:function(){ return window.docx; }},
  'heic2any':{src:'vendor/heic2any.min.js',test:function(){ return window.heic2any; }},
  'xlsx':{src:'vendor/xlsx.min.js',test:function(){ return window.XLSX; }}
};
var V={
  _p:{},
  need:function(name){
    if(this._p[name]) return this._p[name];
    var meta=VENDOR[name];
    var p=new Promise(function(res,rej){
      if(meta.test()){ res(); return; }
      var s=document.createElement('script');
      s.src=meta.src;
      s.onload=function(){ meta.test()?res():rej(new Error('badlib')); };
      s.onerror=function(){ rej(new Error('loadfail')); };
      document.head.appendChild(s);
    });
    if(name==='pdfjs'){
      p=p.then(function(){
        if(window.pdfjsLib&&window.pdfjsLib.GlobalWorkerOptions)
          window.pdfjsLib.GlobalWorkerOptions.workerSrc='vendor/pdfjs.worker.min.js';
      });
    }
    this._p[name]=p; return p;
  },
  pdfLib:function(){ return V.need('pdf-lib'); },
  pdfjs:function(){ return V.need('pdfjs'); },
  mammoth:function(){ return V.need('mammoth'); },
  docx:function(){ return V.need('docx'); },
  heic:function(){ return V.need('heic2any'); },
  xlsx:function(){ return V.need('xlsx'); }
};

/* ================= CV: original document detection pipeline =================
   grayscale -> 5x5 Gaussian -> Sobel -> Otsu -> Hough lines ->
   largest-quad pick -> DLT homography -> bilinear warp.
   Falls back to an inset rectangle when no quad is found.
   Adaptive B&W via integral image. All original code. */
var CV=(function(){
  function gray(px,w,h){
    var g=new Float32Array(w*h);
    for(var i=0;i<w*h;i++) g[i]=0.299*px[i*4]+0.587*px[i*4+1]+0.114*px[i*4+2];
    return g;
  }
  var GAUSS5=[2,4,5,4,2, 4,9,12,9,4, 5,12,15,12,5, 4,9,12,9,4, 2,4,5,4,2];
  function blur(g,w,h){
    var out=new Float32Array(w*h), sum=0, k;
    for(k=0;k<25;k++) sum+=GAUSS5[k];
    for(var y=0;y<h;y++)for(var x=0;x<w;x++){
      var acc=0;
      for(var ky=-2;ky<=2;ky++)for(var kx=-2;kx<=2;kx++){
        var xx=Math.min(w-1,Math.max(0,x+kx)), yy=Math.min(h-1,Math.max(0,y+ky));
        acc+=g[yy*w+xx]*GAUSS5[(ky+2)*5+(kx+2)];
      }
      out[y*w+x]=acc/sum;
    }
    return out;
  }
  /* fast separable binomial blur for the LIVE path only (5+5 taps instead of
     25 — the still-photo path keeps the exact 5x5 above, untouched). */
  function blurSep(g,w,h){
    var tmp=new Float32Array(w*h), out=new Float32Array(w*h), x, y, i, xx, yy, a;
    var k=[1,4,6,4,1];
    for(y=0;y<h;y++)for(x=0;x<w;x++){
      a=0;
      for(i=-2;i<=2;i++){ xx=x+i; if(xx<0)xx=0; else if(xx>=w)xx=w-1; a+=g[y*w+xx]*k[i+2]; }
      tmp[y*w+x]=a/16;
    }
    for(y=0;y<h;y++)for(x=0;x<w;x++){
      a=0;
      for(i=-2;i<=2;i++){ yy=y+i; if(yy<0)yy=0; else if(yy>=h)yy=h-1; a+=tmp[yy*w+x]*k[i+2]; }
      out[y*w+x]=a/16;
    }
    return out;
  }
  function sobelXY(g,w,h){
    var mag=new Float32Array(w*h), gx=new Float32Array(w*h), gy=new Float32Array(w*h);
    for(var y=1;y<h-1;y++)for(var x=1;x<w-1;x++){
      var i=y*w+x;
      var gxx=-g[i-w-1]-2*g[i-1]-g[i+w-1]+g[i-w+1]+2*g[i+1]+g[i+w+1];
      var gyy=-g[i-w-1]-2*g[i-w]-g[i-w+1]+g[i+w-1]+2*g[i+w]+g[i+w+1];
      gx[i]=gxx; gy[i]=gyy; mag[i]=Math.sqrt(gxx*gxx+gyy*gyy);
    }
    return {m:mag,x:gx,y:gy};
  }
  function sobel(g,w,h){ return sobelXY(g,w,h).m; }
  function otsu(mag,w,h){
    var hist=new Uint32Array(256), max=0, i;
    for(i=0;i<w*h;i++) if(mag[i]>max) max=mag[i];
    if(max<=0) return 1;
    for(i=0;i<w*h;i++) hist[Math.min(255,(mag[i]/max*255)|0)]++;
    var total=w*h, sum=0;
    for(i=0;i<256;i++) sum+=i*hist[i];
    var sumB=0,wB=0,best=0,thresh=1;
    for(i=0;i<256;i++){
      wB+=hist[i]; if(!wB) continue;
      var wF=total-wB; if(!wF) break;
      sumB+=i*hist[i];
      var mB=sumB/wB, mF=(sum-sumB)/wF, d=mB-mF;
      var between=wB*wF*d*d;
      if(between>best){ best=between; thresh=i; }
    }
    return (thresh/255)*max||1;
  }
  function hough(edge,w,h){
    var diag=Math.sqrt(w*w+h*h), nrd=Math.ceil(diag), nr=2*nrd+1, nth=180;
    var acc=new Float32Array(nr*nth);
    var cos=new Float32Array(nth), sin=new Float32Array(nth);
    for(var th=0;th<nth;th++){ var r=th*Math.PI/nth; cos[th]=Math.cos(r); sin[th]=Math.sin(r); }
    for(var y=0;y<h;y+=2)for(var x=0;x<w;x+=2){
      if(!edge[y*w+x]) continue;
      for(var tt=0;tt<nth;tt+=2){
        var ri=Math.round(x*cos[tt]+y*sin[tt])+nrd;
        if(ri>=0&&ri<nr) acc[ri*nth+tt]++;
      }
    }
    var lines=[];
    for(var k=0;k<40;k++){
      var bi=0,bv=0;
      for(var i2=0;i2<nr*nth;i2++) if(acc[i2]>bv){ bv=acc[i2]; bi=i2; }
      if(bv<8) break;
      var bri=((bi/nth)|0)-nrd, bth=bi%nth;
      /* NOTE: rho stays SIGNED here. With theta in [0,PI) a line's rho is the
         signed distance from the origin along its normal — forcing rho>=0
         would map distinct parallel lines onto each other. */
      lines.push({rho:bri,theta:bth*Math.PI/nth,votes:bv});
      for(var dr=-6;dr<=6;dr++)for(var dt=-6;dt<=6;dt++){
        var rr=bri+dr+nrd, t2=bth+dt;
        if(rr>=0&&rr<nr&&t2>=0&&t2<nth) acc[rr*nth+t2]=0;
      }
    }
    return lines;
  }
  function lineIntersect(l1,l2){
    var c1=Math.cos(l1.theta),s1=Math.sin(l1.theta),c2=Math.cos(l2.theta),s2=Math.sin(l2.theta);
    var det=c1*s2-s1*c2;
    if(Math.abs(det)<1e-6) return null;
    return {x:(l1.rho*s2-s1*l2.rho)/det, y:(c1*l2.rho-l1.rho*c2)/det};
  }
  function quadArea(q){
    var a=0;
    for(var i=0;i<4;i++){ var p=q[i],n2=q[(i+1)%4]; a+=p.x*n2.y-n2.x*p.y; }
    return Math.abs(a/2);
  }
  function pickQuad(lines,w,h){
    var pts=[];
    for(var i=0;i<lines.length;i++)for(var j=i+1;j<lines.length;j++){
      var d=Math.abs(lines[i].theta-lines[j].theta);
      d=Math.min(d,Math.PI-d);
      if(d<0.35) continue;
      var p=lineIntersect(lines[i],lines[j]);
      if(p&&p.x>-w*0.2&&p.x<w*1.2&&p.y>-h*0.2&&p.y<h*1.2) pts.push(p);
    }
    if(pts.length<4) return null;
    pts.sort(function(a,b){ return a.x-b.x||a.y-b.y; });
    function cross(o,a,b){ return (a.x-o.x)*(b.y-o.y)-(a.y-o.y)*(b.x-o.x); }
    var lower=[],upper=[],k,p2;
    for(k=0;k<pts.length;k++){ p2=pts[k];
      while(lower.length>=2&&cross(lower[lower.length-2],lower[lower.length-1],p2)<=0) lower.pop();
      lower.push(p2); }
    for(k=pts.length-1;k>=0;k--){ p2=pts[k];
      while(upper.length>=2&&cross(upper[upper.length-2],upper[upper.length-1],p2)<=0) upper.pop();
      upper.push(p2); }
    lower.pop(); upper.pop();
    var hull=lower.concat(upper);
    if(hull.length<4) return null;
    var tl=hull[0],tr=hull[0],br=hull[0],bl=hull[0];
    hull.forEach(function(p){
      if(p.x+p.y<tl.x+tl.y) tl=p;
      if(p.x-p.y>tr.x-tr.y) tr=p;
      if(p.x+p.y>br.x+br.y) br=p;
      if(p.x-p.y<bl.x-bl.y) bl=p;
    });
    var q=[tl,tr,br,bl];
    if(quadArea(q)<w*h*0.05) return null;
    return q;
  }
  function detectQuad(px,w,h){
    try{
      var g=gray(px,w,h), b=blur(g,w,h), sm=sobelXY(b,w,h);
      var r=searchQuads(sm,w,h,g,otsu(sm.m,w,h));
      if(r.kept.length) return r.kept[0].q;
    }catch(e){}
    var mx=w*0.04, my=h*0.04;
    return [{x:mx,y:my},{x:w-mx,y:my},{x:w-mx,y:h-my},{x:mx,y:h-my}];
  }
  /* ============ paper-aware LIVE detection (viewfinder) ============
     The still-photo detectQuad() above just takes the LARGEST quad from all
     line intersections — in a busy live viewfinder that latches onto screen
     edges, table lines, anything big (the "wild quad" bug). For live frames
     we generate CANDIDATE quads from parallel line pairs and score them like
     a brain: only paper-shaped quads win. */
  function orderQuad(q){
    var cx=0,cy=0,i;
    for(i=0;i<4;i++){ cx+=q[i].x; cy+=q[i].y; }
    cx/=4; cy/=4;
    var s=q.slice().sort(function(a,b){
      return Math.atan2(a.y-cy,a.x-cx)-Math.atan2(b.y-cy,b.x-cx); });
    /* start at the corner nearest top-left: stable corner correspondence for EMA */
    var bi=0,bv=1e18;
    for(i=0;i<4;i++){ var v=s[i].x+s[i].y; if(v<bv){ bv=v; bi=i; } }
    return s.slice(bi).concat(s.slice(0,bi));
  }
  function inPoly(x,y,q){
    var inside=false,i,j;
    for(i=0,j=3;i<4;j=i++){
      var xi=q[i].x,yi=q[i].y,xj=q[j].x,yj=q[j].y;
      if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi)) inside=!inside;
    }
    return inside;
  }
  /* Moore-neighbor boundary tracing on the binary edge map. Returns the
     boundary loops (arrays of {x,y}); fragmented texture edges yield short
     loops that never survive the perimeter gate in contourQuads. */
  function traceContours(edge,w,h){
    var seen=new Uint8Array(w*h), out=[];
    var DX=[1,1,0,-1,-1,-1,0,1], DY=[0,1,1,1,0,-1,-1,-1];
    for(var y=1;y<h-1;y++)for(var x=1;x<w-1;x++){
      var si=y*w+x;
      if(!edge[si]||seen[si]||edge[si-1]) continue;
      var pts=[],cx=x,cy=y,px=x-1,py=y,guard=0;
      for(;;){
        pts.push({x:cx,y:cy}); seen[cy*w+cx]=1;
        var dx=cx-px,dy=cy-py,d=0,k;
        for(k=0;k<8;k++) if(DX[k]===dx&&DY[k]===dy){ d=k; break; }
        /* Moore rule: examine neighbors clockwise starting AFTER the pixel
           we came from (prev sits at (d+4)&7 from here, so start at (d+5)&7) */
        var found=false,nx=0,ny=0;
        for(var s=0;s<8;s++){
          var nd=(d+5+s)&7,tx=cx+DX[nd],ty=cy+DY[nd];
          if(tx<0||ty<0||tx>=w||ty>=h) continue;
          if(edge[ty*w+tx]){ nx=tx; ny=ty; found=true; break; }
        }
        if(!found) break;
        px=cx; py=cy; cx=nx; cy=ny;
        if(cx===x&&cy===y&&pts.length>12) break;
        if(++guard>6000) break;
      }
      if(pts.length>=48) out.push(pts);
      if(out.length>=24) return out;
    }
    return out;
  }
  /* Douglas-Peucker on a closed loop -> simplified polygon.
     The loop is split at the point farthest from the start so the two
     halves are genuine open polylines (a degenerate zero-length first
     segment would never split and the loop would collapse to 1 point). */
  function approxClosed(pts,eps){
    var n=pts.length,bi=0,bv=1e18,i;
    for(i=0;i<n;i++){ var v=pts[i].x+pts[i].y; if(v<bv){ bv=v; bi=i; } }
    var sx=pts[bi].x, sy=pts[bi].y, fi=bi, fd=0;
    for(i=0;i<n;i++){
      var dd=(pts[i].x-sx)*(pts[i].x-sx)+(pts[i].y-sy)*(pts[i].y-sy);
      if(dd>fd){ fd=dd; fi=i; }
    }
    function dpOpen(idx){
      var m=idx.length, keep=new Uint8Array(m), st=[[0,m-1]], k;
      keep[0]=keep[m-1]=1;
      while(st.length){
        var sg=st.pop(), a=sg[0], b=sg[1];
        var pa=pts[idx[a]], pb=pts[idx[b]];
        var dx=pb.x-pa.x, dy=pb.y-pa.y, len=Math.sqrt(dx*dx+dy*dy)||1e-9;
        var dmax=0, imax=-1;
        for(k=a+1;k<b;k++){
          var pk=pts[idx[k]];
          var d=Math.abs((pk.x-pa.x)*dy-(pk.y-pa.y)*dx)/len;
          if(d>dmax){ dmax=d; imax=k; }
        }
        if(dmax>eps){ keep[imax]=1; st.push([a,imax]); st.push([imax,b]); }
      }
      var out=[];
      for(k=0;k<m;k++) if(keep[k]) out.push(pts[idx[k]]);
      return out;
    }
    var idx1=[], idx2=[], i2=bi;
    for(;;){ idx1.push(i2); if(i2===fi) break; i2=(i2+1)%n; }
    i2=fi;
    for(;;){ idx2.push(i2); if(i2===bi) break; i2=(i2+1)%n; }
    var p1=dpOpen(idx1), p2=dpOpen(idx2);
    return p1.concat(p2.slice(1,-1));
  }
  /* Four-sided loops straight from the edge map — the "exact four sides"
     path: no Hough lines needed, the boundary itself is the quad. */
  function contourQuads(edge,w,h){
    var cs=traceContours(edge,w,h),out=[],i,k;
    var minPer=Math.min(w,h)*0.9;
    for(i=0;i<cs.length;i++){
      var c=cs[i],per=0;
      for(k=0;k<c.length;k++){ var a=c[k],b=c[(k+1)%c.length];
        per+=Math.sqrt((a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)); }
      if(per<minPer) continue;
      var poly=approxClosed(c,per*0.02);
      if(poly.length!==4) continue;
      out.push(orderQuad(poly));
      if(out.length>=12) break;
    }
    return out;
  }
  /* Area-average downscale (pure JS: no canvas, node-QA safe). */
  function downscale(px,w,h,dw,dh){
    var out=new Uint8ClampedArray(dw*dh*4),x,y,c;
    var sx=w/dw, sy=h/dh;
    for(y=0;y<dh;y++)for(x=0;x<dw;x++){
      var x0=Math.floor(x*sx),x1=Math.min(w,Math.ceil((x+1)*sx));
      var y0=Math.floor(y*sy),y1=Math.min(h,Math.ceil((y+1)*sy));
      var r=0,g=0,b=0,n=0,yy,xx;
      for(yy=y0;yy<y1;yy++)for(xx=x0;xx<x1;xx++){
        var o=(yy*w+xx)*4; r+=px[o]; g+=px[o+1]; b+=px[o+2]; n++;
      }
      var oo=(y*dw+x)*4;
      out[oo]=r/n; out[oo+1]=g/n; out[oo+2]=b/n; out[oo+3]=255;
    }
    return out;
  }
  /* Snap each side of a candidate quad to the true edge: sample along the
     side, find the peak gradient within +-R px of each sample, fit a line
     through the peaks (least squares), intersect the four lines. Returns the
     refined quad or null when a side is not a straight edge. */
  function refineQuad(q, sm, eth, w, h){
    var mag=sm.m, lines=[], s, i, j;
    var ccx=0, ccy=0;
    for(var cs=0;cs<4;cs++){ ccx+=q[cs].x; ccy+=q[cs].y; }
    ccx/=4; ccy/=4;
    for(s=0;s<4;s++){
      var A=q[s], B=q[(s+1)%4];
      var ex=B.x-A.x, ey=B.y-A.y, len=Math.hypot(ex,ey)||1e-9;
      var nx=-ey/len, ny=ex/len, pts=[];
      var N=24, R=14;
      for(i=0;i<N;i++){
        var t=(i+0.5)/N, bx=A.x+ex*t, by=A.y+ey*t;
        /* outward = away from the quad centroid: the paper boundary is the
           outermost strong edge (this beats latching onto title bars/text) */
        var outSign=((bx-ccx)*nx+(by-ccy)*ny)>=0?1:-1;
        var bestD=null, bestOut=-1e9;
        for(var d=-R;d<=R;d++){
          var xi=Math.round(bx+nx*d), yi=Math.round(by+ny*d);
          if(xi<0||xi>=w||yi<0||yi>=h) continue;
          if(mag[yi*w+xi]>eth){
            var outness=d*outSign;
            if(outness>bestOut){ bestOut=outness; bestD=d; }
          }
        }
        if(bestD!==null) pts.push({x:bx+nx*bestD, y:by+ny*bestD});
      }
      if(pts.length<10) return null;
      var sx=0, sy=0, n=pts.length;
      for(j=0;j<n;j++){ sx+=pts[j].x; sy+=pts[j].y; }
      sx/=n; sy/=n;
      var sxx=0, sxy=0, syy=0;
      for(j=0;j<n;j++){ var dx=pts[j].x-sx, dy=pts[j].y-sy; sxx+=dx*dx; sxy+=dx*dy; syy+=dy*dy; }
      var line, res=0;
      if(sxx>=syy){ var m0=sxy/(sxx||1e-9); line={m:m0,b:sy-m0*sx,v:0};
        for(j=0;j<n;j++) res+=Math.abs(pts[j].y-(m0*pts[j].x+line.b));
      }else{ var m1=sxy/(syy||1e-9); line={m:m1,b:sx-m1*sy,v:1};
        for(j=0;j<n;j++) res+=Math.abs(pts[j].x-(m1*pts[j].y+line.b)); }
      if(res/n>3) return null;
      lines.push(line);
    }
    function isect(l1,l2){
      var a1,b1,c1,a2,b2,c2;
      if(!l1.v){ a1=-l1.m; b1=1; c1=l1.b; } else { a1=1; b1=-l1.m; c1=l1.b; }
      if(!l2.v){ a2=-l2.m; b2=1; c2=l2.b; } else { a2=1; b2=-l2.m; c2=l2.b; }
      var det=a1*b2-a2*b1;
      if(Math.abs(det)<1e-9) return null;
      return {x:(c1*b2-c2*b1)/det, y:(a1*c2-a2*c1)/det};
    }
    var out=[];
    for(s=0;s<4;s++){
      var p=isect(lines[s],lines[(s+1)%4]);
      if(!p||p.x<-w*0.1||p.x>w*1.1||p.y<-h*0.1||p.y>h*1.1) return null;
      out.push(p);
    }
    return orderQuad(out);
  }
  /* Capture-time refinement: the live tracker quad comes from 320px-wide
     frames with EMA smoothing — good for the overlay, but its corners are
     too coarse for a level warp at full resolution. Re-snap the quad on the
     captured still (at ~1000px, then scaled back): each side is edge-snapped
     and corners re-intersected, exactly like CamScanner's capture refine.
     Returns the refined quad in full-res coords, or null (caller keeps the
     live quad). */
  function refineCapture(px,w,h,liveQ){
    try{
      if(!liveQ||liveQ.length!==4) return null;
      var TW=1000, ds=w>TW?TW/w:1;
      var dw=Math.max(1,Math.round(w*ds)), dh=Math.max(1,Math.round(h*ds));
      var spx=ds<1?downscale(px,w,h,dw,dh):px;
      var g=gray(spx,dw,dh), b=blur(g,dw,dh), sm=sobelXY(b,dw,dh);
      var eth=otsu(sm.m,dw,dh);
      var q=liveQ.map(function(p){ return {x:p.x*ds, y:p.y*ds}; });
      var rq=refineQuad(q,sm,eth,dw,dh);
      if(!rq) return null;
      /* sanity: refined corners must stay near the live seed (no wild jump) */
      var maxD=Math.max(dw,dh)*0.12, i;
      for(i=0;i<4;i++){
        if(Math.hypot(rq[i].x-q[i].x,rq[i].y-q[i].y)>maxD) return null;
      }
      var us=1/ds;
      return rq.map(function(p){ return {x:p.x*us, y:p.y*us}; });
    }catch(e){ return null; }
  }
  function genCandidates(lines,w,h){
    var cands=[],i,j,k,p;
    /* Angle-diverse line pool: the top votes are often all one edge family
       (adjacent theta bins of the same strong edge), which starves the cross
       family and yields only degenerate quads. Keep the top 10 by votes,
       then add up to 8 more lines from clearly different orientations so both
       edge families of a sheet are always represented. */
    var sorted=lines.slice().sort(function(a,b){ return b.votes-a.votes; });
    /* drop near-duplicate detections of the same physical edge (adjacent
       theta/rho bins, theta-wrap duplicates). Comparison is sign-aware:
       (rho,theta) ~ (-rho,theta+PI) describe the same line. */
    var uniq=[];
    for(i=0;i<sorted.length;i++){
      var keep=true, li=sorted[i];
      var c1=Math.cos(li.theta), s1=Math.sin(li.theta);
      for(var u2=0;u2<uniq.length;u2++){
        var lj=uniq[u2];
        var dot=c1*Math.cos(lj.theta)+s1*Math.sin(lj.theta);
        if(Math.abs(dot)<Math.cos(0.12)) continue; /* not parallel */
        var sg=dot>0?1:-1;
        if(Math.abs(li.rho-sg*lj.rho)<14){ keep=false; break; }
      }
      if(keep) uniq.push(li);
    }
    var ls=[];
    for(i=0;i<uniq.length&&ls.length<10;i++) ls.push(uniq[i]);
    var dom=ls.length?ls[0].theta:0;
    for(i=0;i<uniq.length&&ls.length<18;i++){
      var l=uniq[i];
      if(ls.indexOf(l)>=0) continue;
      var dd=Math.abs(l.theta-dom); dd=Math.min(dd,Math.PI-dd);
      if(dd>0.5) ls.push(l);
    }
    var pairs=[];
    for(i=0;i<ls.length;i++)for(j=i+1;j<ls.length;j++){
      var d=Math.abs(ls[i].theta-ls[j].theta); d=Math.min(d,Math.PI-d);
      if(d<0.22) pairs.push([ls[i],ls[j]]);
    }
    for(i=0;i<pairs.length;i++)for(j=0;j<pairs.length;j++){
      if(i===j) continue;
      var a1=pairs[i][0],a2=pairs[i][1],b1=pairs[j][0],b2=pairs[j][1];
      if(a1===b1||a1===b2||a2===b1||a2===b2) continue; /* shared line -> degenerate */
      var d0=Math.abs(a1.theta-b1.theta); d0=Math.min(d0,Math.PI-d0);
      if(d0<0.5) continue; /* the two families must not be parallel */
      var cs=[lineIntersect(a1,b1),lineIntersect(a1,b2),lineIntersect(a2,b1),lineIntersect(a2,b2)];
      var ok=true;
      for(k=0;k<4;k++){ p=cs[k];
        if(!p||p.x<-w*0.05||p.x>w*1.05||p.y<-h*0.05||p.y>h*1.05){ ok=false; break; } }
      if(!ok) continue;
      cands.push(orderQuad(cs));
      if(cands.length>=240) return cands;
    }
    return cands;
  }
  /* paper-likeness score 0..1 (0 = reject). A real sheet of paper is convex,
     has A4/Letter-ish aspect, covers a sane frame area, has ~90° corners,
     sits on strong contrast edges, and does NOT touch the frame border.
     Pass an object as `out` and it is filled with the per-term breakdown
     (or out.fail = the rejecting term) for QA/debugging. */
  function quadScore(q,w,h,sm,eth,ed,gry,out){
    var mag=sm.m, i, p;
    function rej(why){ if(out) out.fail=why; return 0; }
    for(i=0;i<4;i++){ p=q[i];
      if(p.x<0||p.x>w||p.y<0||p.y>h) return rej('outside'); }
    var s0=0;
    for(i=0;i<4;i++){
      var a=q[i],b=q[(i+1)%4],c=q[(i+2)%4];
      var cr=(b.x-a.x)*(c.y-b.y)-(b.y-a.y)*(c.x-b.x);
      if(Math.abs(cr)<1e-9) return rej('degenerate');
      var s=cr>0?1:-1;
      if(s0===0) s0=s; else if(s!==s0) return rej('concave');
    }
    var af=quadArea(q)/(w*h);
    var areaS=af<0.04||af>0.97?0:(af<0.08?0.3+(af-0.04)/0.04*0.7:(af>0.85?Math.max(0.3,1-(af-0.85)/0.12*0.7):1));
    if(!areaS) return rej('area');
    var L=[];
    for(i=0;i<4;i++){ var u=q[i],v=q[(i+1)%4];
      L.push(Math.hypot(u.x-v.x,u.y-v.y)); }
    if(Math.min.apply(null,L)<Math.max(w,h)*0.05) return rej('sliver'); /* sliver, not paper */
    var wA=(L[0]+L[2])/2, hA=(L[1]+L[3])/2;
    var aspect=Math.max(wA,hA)/Math.max(1e-6,Math.min(wA,hA));
    /* A4, Letter, and square: many journals/notebooks are square-ish, and
       rejecting them outright made real documents undetectable. The other
       gates (edges, contrast, texture) still kill non-paper rectangles. */
    var dA=Math.min(Math.abs(aspect-1.4142),Math.abs(aspect-1.2941),Math.abs(aspect-1.0));
    var aspS=Math.exp(-Math.pow(dA/0.20,2));
    if(aspS<0.25) return rej('aspect');
    var angS=1;
    for(i=0;i<4;i++){
      var p0=q[i],p1=q[(i+1)%4],p2=q[(i+2)%4];
      var v1x=p0.x-p1.x,v1y=p0.y-p1.y,v2x=p2.x-p1.x,v2y=p2.y-p1.y;
      var n1=Math.hypot(v1x,v1y)||1e-9,n2=Math.hypot(v2x,v2y)||1e-9;
      var ang=Math.acos(Math.max(-1,Math.min(1,(v1x*v2x+v1y*v2y)/(n1*n2))))*180/Math.PI;
      var dd=Math.abs(ang-90);
      angS*=dd<10?1:(dd>32?0:1-(dd-10)/22);
    }
    if(!angS) return rej('angles');
    var sideS=[],sideRun=[],hit=0,tot=0;
    for(i=0;i<4;i++){
      var A2=q[i],B2=q[(i+1)%4],sh2=0,stn2=0,run2=0,best2=0;
      for(var s2=0;s2<28;s2++){
        var fx=A2.x+(B2.x-A2.x)*s2/27, fy=A2.y+(B2.y-A2.y)*s2/27;
        var xi=Math.round(fx), yi=Math.round(fy);
        if(xi<1||xi>=w-1||yi<1||yi>=h-1){ run2=0; continue; }
        stn2++;
        /* 3x3 dilated edge test for the per-side gates: a true side 1px off
           the edge line still counts (the tracker refines subpixel quads) */
        var ehit=0;
        for(var dy2=-1;dy2<=1&&!ehit;dy2++)for(var dx2=-1;dx2<=1;dx2++)
          if(mag[(yi+dy2)*w+xi+dx2]>eth){ ehit=1; break; }
        if(ehit){ sh2++; run2++; if(run2>best2) best2=run2; }
        else run2=0;
        /* single-pixel support feeds the overall sup (score + texture gate) */
        tot++; if(mag[yi*w+xi]>eth) hit++;
      }
      sideS.push(stn2?sh2/stn2:0); sideRun.push(best2);
    }
    var sup=tot?hit/tot:0;
    /* Every side should be a real edge — but a real sheet photographed in a
       real room can have ONE weak side (shadow, glare, or an edge lying
       against a similar-colored background). Reject only when TWO or more
       sides are weak: sort and gate on the 2nd-weakest. The remaining gates
       below (orientation, support, contrast, texture, flat) still kill
       hallucinated rectangles, so this softening costs no false positives. */
    var sSorted=sideS.slice().sort(function(a,b){ return a-b; });
    if(sSorted[1]<Math.max(0.25,(ed||0)*1.6)) return rej('side');
    /* ...and each side should be CONTINUOUS: a true page edge gives a long
       unbroken run of edge pixels; accidental alignments of texture (grille
       rings crossing an imaginary line) give scattered hits. Same one-weak-
       side allowance: gate on the 2nd-weakest run, floor lowered 8->6 for
       noisy 320px live frames where real edges are 1-2px wide. */
    var rSorted=sideRun.slice().sort(function(a,b){ return a-b; });
    if(rSorted[1]<6) return rej('run');
    /* gradient orientation coherence: along a true page edge every gradient
       points (anti-)parallel to the side normal; texture edges point every
       which way. Mean |cos| ~0.95+ for a real edge, ~0.64 for noise. */
    var gxx=sm.x, gyy=sm.y;
    for(i=0;i<4;i++){
      var A3=q[i],B3=q[(i+1)%4];
      var ex=B3.x-A3.x, ey=B3.y-A3.y, el=Math.hypot(ex,ey)||1e-9;
      var nx=-ey/el, ny=ex/el, cSum=0, cN=0;
      for(var s3=0;s3<28;s3++){
        var xi3=Math.round(A3.x+ex*s3/27), yi3=Math.round(A3.y+ey*s3/27);
        if(xi3<1||yi3<1||xi3>=w-1||yi3>=h-1) continue;
        var gi=yi3*w+xi3, gx2=gxx[gi], gy2=gyy[gi];
        var gm=Math.sqrt(gx2*gx2+gy2*gy2);
        if(gm<eth) continue;
        cSum+=Math.abs((gx2*nx+gy2*ny)/gm); cN++;
      }
      if(cN>=6&&cSum/cN<0.75) return rej('orient');
    }
    /* the quad's edges must stand out from the background clutter: in pure
       noise ~40% of pixels are "edges", so random quads score ~0.4 support.
       A real sheet's edges are far denser than the frame average. */
    var supNeed=Math.max(0.35,(ed||0)*2.2+0.18);
    if(sup<supNeed) return rej('support');
    /* edge CONTRAST: a real sheet separates paper from background — the mean
       |inside-outside| brightness step along its edges is large. A rectangle
       hallucinated on a random texture (checkerboard, carpet weave) has no
       consistent step: inside and outside look the same. */
    var ccx=0,ccy=0;
    for(i=0;i<4;i++){ ccx+=q[i].x; ccy+=q[i].y; }
    ccx/=4; ccy/=4;
    var csum=0,cn=0;
    for(i=0;i<4;i++){
      var E1=q[i],E2=q[(i+1)%4];
      var ex=E2.x-E1.x, ey=E2.y-E1.y, el=Math.hypot(ex,ey)||1e-9;
      var nx=-ey/el, ny=ex/el, mx2=(E1.x+E2.x)/2, my2=(E1.y+E2.y)/2;
      if(nx*(mx2-ccx)+ny*(my2-ccy)<0){ nx=-nx; ny=-ny; } /* outward */
      for(var sc2=0;sc2<14;sc2++){
        var t3=0.1+0.8*sc2/13;
        var sx=E1.x+ex*t3, sy=E1.y+ey*t3;
        var ox=Math.round(sx+nx*4), oy=Math.round(sy+ny*4);
        var ix2=Math.round(sx-nx*4), iy2=Math.round(sy-ny*4);
        if(ox<0||ox>=w||oy<0||oy>=h||ix2<0||ix2>=w||iy2<0||iy2>=h) continue;
        csum+=Math.abs(gry[oy*w+ox]-gry[iy2*w+ix2]); cn++;
      }
    }
    /* A real sheet separates from its background, but the step can be modest
       (~20) when the cover is mid-tone against a soft background — the old
       floor of 30 rejected genuine documents. 18 still rejects rectangles
       hallucinated on uniform texture (their step is ~5-12, just noise). */
    if(cn>0&&csum/cn<18) return rej('contrast');
    /* border-vs-interior: a page boundary is far denser in edges than the
       page interior. A rectangle hallucinated on busy texture (fan grilles,
       carpet weave) has strong edges everywhere -> reject. */
    var qx0=1e9,qy0=1e9,qx1=-1e9,qy1=-1e9;
    for(i=0;i<4;i++){ qx0=Math.min(qx0,q[i].x); qy0=Math.min(qy0,q[i].y);
      qx1=Math.max(qx1,q[i].x); qy1=Math.max(qy1,q[i].y); }
    var inHit=0,inTot=0;
    for(var gy3=0;gy3<6;gy3++)for(var gx3=0;gx3<6;gx3++){
      var px3=qx0+(qx1-qx0)*(gx3+0.5)/6, py3=qy0+(qy1-qy0)*(gy3+0.5)/6;
      var ix3=Math.round(px3), iy3=Math.round(py3);
      if(ix3<2||iy3<2||ix3>=w-2||iy3>=h-2||!inPoly(ix3,iy3,q)) continue;
      var dmin=1e9;
      for(var e3=0;e3<4;e3++){
        var P2=q[e3],Q2=q[(e3+1)%4];
        var vx=Q2.x-P2.x, vy=Q2.y-P2.y, L2=vx*vx+vy*vy||1e-9;
        var tt=((ix3-P2.x)*vx+(iy3-P2.y)*vy)/L2; tt=tt<0?0:(tt>1?1:tt);
        var ddx=ix3-(P2.x+vx*tt), ddy=iy3-(P2.y+vy*tt);
        var dd2=Math.sqrt(ddx*ddx+ddy*ddy);
        if(dd2<dmin) dmin=dd2;
      }
      if(dmin<6) continue; /* too close to the border to count as interior */
      inTot++; if(mag[iy3*w+ix3]>eth) inHit++;
    }
    var inDens=inTot?inHit/inTot:0;
    if(sup/Math.max(inDens,0.04)<2.2) return rej('texture');
    /* brightness step: a document interior is a coherent region distinctly
       brighter or darker than its surround. A rectangle hallucinated on
       uniform texture (checkerboard, weave) has no step -> reject. */
    var inM=0,inN=0;
    for(var by4=0;by4<8;by4++)for(var bx4=0;bx4<8;bx4++){
      var qx4=qx0+(qx1-qx0)*(bx4+0.5)/8, qy4=qy0+(qy1-qy0)*(by4+0.5)/8;
      var ix4=Math.round(qx4), iy4=Math.round(qy4);
      if(ix4<0||iy4<0||ix4>=w||iy4>=h||!inPoly(ix4,iy4,q)) continue;
      inM+=gry[iy4*w+ix4]; inN++;
    }
    var ex0=Math.max(0,Math.floor(qx0-14)), ey0=Math.max(0,Math.floor(qy0-14));
    var ex1=Math.min(w-1,Math.ceil(qx1+14)), ey1=Math.min(h-1,Math.ceil(qy1+14));
    var outM=0,outN=0;
    for(var oy5=ey0;oy5<=ey1;oy5+=6)for(var ox5=ex0;ox5<=ex1;ox5+=6){
      var ix5=Math.round(ox5), iy5=Math.round(oy5);
      if(ix5<0||iy5<0||ix5>=w||iy5>=h||inPoly(ix5,iy5,q)) continue;
      outM+=gry[iy5*w+ix5]; outN++;
    }
    if(outN>8&&inN>8&&Math.abs(inM/inN-outM/outN)<15) return rej('flat');
    /* 0.3x penalty when the quad runs into the frame border (the wild-quad
       signature). The zone is tight (1%): a real sheet sitting a few px off
       the edge is legitimate and must not be penalized. */
    var mrg=Math.min(w,h), touch=false;
    for(i=0;i<4;i++){ p=q[i];
      if(p.x<mrg*0.01||p.x>w-mrg*0.01||p.y<mrg*0.01||p.y>h-mrg*0.01){ touch=true; break; } }
    if(!touch) for(i=0;i<4;i++){
      var mx=(q[i].x+q[(i+1)%4].x)/2, my=(q[i].y+q[(i+1)%4].y)/2;
      if(mx<mrg*0.0075||mx>w-mrg*0.0075||my<mrg*0.0075||my>h-mrg*0.0075){ touch=true; break; } }
    if(out) out.terms={areaS:+areaS.toFixed(3),aspS:+aspS.toFixed(3),angS:+angS.toFixed(3),sup:+sup.toFixed(3),touch:touch?1:0};
    return aspS*areaS*angS*(0.25+0.75*sup)*(touch?0.3:1);
  }
  function guideRect(w,h){
    var gh=h*0.62, gw=gh/1.4142;
    if(gw>w*0.9){ gw=w*0.9; gh=gw*1.4142; }
    var x0=(w-gw)/2, y0=(h-gh)/2;
    return [{x:x0,y:y0},{x:x0+gw,y:y0},{x:x0+gw,y:y0+gh},{x:x0,y:y0+gh}];
  }
  /* Live frame -> {q: smoothed quad in frame px (or null), score, guide}.
     Temporal policy: adopt the first paper-like quad; afterwards only switch
     to an overlapping candidate that scores clearly better (EMA blend, never
     a snap); a far-away candidate needs a much better score (user moved to a
     different sheet). On detection loss the last good quad freezes ~2.4s,
     then we fall back to the aim guide — never to a wild quad. */
  /* Score every candidate quad for one live frame. Returns
     {kept:[{q,s,parts}], nLines, nCands}. Used by detectLive and by the
     _dbgLive QA hook below. */
  /* Multi-threshold quad search shared by the live and still paths: tries
     Otsu, a lower threshold (faint edges) and a higher one (clutter
     suppression); contour quads + Hough line-pair quads compete under the
     same strict paper score. Returns the scored/deduped candidate list. */
  function searchQuads(sm,w,h,g,th0,keepAll){
    var mag=sm.m, ths=[th0,th0*0.72,th0*1.38];
    var kept=[],rejH={},nLines=0,nCands=0,ed0=0,topLines=null;
    for(var ti=0;ti<ths.length;ti++){
      var th=ths[ti],edge=new Uint8Array(w*h),i,ne=0;
      for(i=0;i<w*h;i++){ if(mag[i]>th){ edge[i]=1; ne++; } }
      var ed=ne/(w*h);
      if(ti===0) ed0=ed;
      if(ed<0.004||ed>0.5) continue;
      var lines=hough(edge,w,h);
      if(ti===0){ nLines=lines.length;
        topLines=lines.slice(0,14).map(function(l){ return {t:+l.theta.toFixed(3),r:Math.round(l.rho),v:l.votes}; }); }
      var cands=genCandidates(lines,w,h),cq=contourQuads(edge,w,h);
      for(i=0;i<cq.length;i++){ cq[i]._src='contour'; cands.push(cq[i]); }
      try{ var hq=pickQuad(lines,w,h); if(hq){ hq=orderQuad(hq); hq._src='pick'; cands.push(hq); } }catch(e){}
      nCands+=cands.length;
      for(i=0;i<cands.length;i++){
        /* snap the candidate to the true edges before the strict gates see
           it; skip refinement for hopeless (tiny/huge) quads */
        var af0=quadArea(cands[i])/(w*h);
        var rq=(af0>0.04&&af0<0.97)?refineQuad(cands[i],sm,th,w,h):null;
        var qc=rq||cands[i];
        var parts={},s=quadScore(qc,w,h,sm,th,ed,g,parts);
        if(s<=0.30){ var fr2=parts.fail||'?'; rejH[fr2]=(rejH[fr2]||0)+1;
          if(keepAll) kept.push({q:qc,s:0,fail:fr2,src:(cands[i]._src||'hough')+':t'+ti});
          continue; }
        var dup=false;
        for(var k=0;k<kept.length;k++){
          var dd=0;
          for(var c=0;c<4;c++) dd+=Math.hypot(qc[c].x-kept[k].q[c].x,qc[c].y-kept[k].q[c].y);
          if(dd<24){ dup=true; if(s>kept[k].s) kept[k]={q:qc,s:s,parts:parts}; break; }
        }
        if(!dup) kept.push({q:qc,s:s,parts:parts,src:cands[i]._src||'hough'});
      }
      kept.sort(function(a,b2){ return b2.s-a.s; });
      if(!keepAll&&kept.length&&kept[0].s>0.75) break; /* confident: skip extra thresholds */
    }
    kept.sort(function(a,b3){ return b3.s-a.s; });
    return {kept:kept, nLines:nLines, nCands:nCands, rej:rejH, edgeDens:+ed0.toFixed(4),
      topLines:topLines};
  }
  function scoreCandidates(px,w,h){
    var g=gray(px,w,h), b=blurSep(g,w,h), sm=sobelXY(b,w,h);
    return searchQuads(sm,w,h,g,otsu(sm.m,w,h));
  }
  function detectLive(px,w,h,state){
    state=state||{q:null,score:0,lost:0};
    var best=null,bestS=0;
    try{
      var r=scoreCandidates(px,w,h);
      if(r.kept.length){ best=r.kept[0].q; bestS=r.kept[0].s; }
    }catch(e){}
    function boxIoU(a,b){
      var ax0=1e9,ay0=1e9,ax1=-1e9,ay1=-1e9,bx0=1e9,by0=1e9,bx1=-1e9,by1=-1e9,j;
      for(j=0;j<4;j++){
        ax0=Math.min(ax0,a[j].x); ay0=Math.min(ay0,a[j].y);
        ax1=Math.max(ax1,a[j].x); ay1=Math.max(ay1,a[j].y);
        bx0=Math.min(bx0,b[j].x); by0=Math.min(by0,b[j].y);
        bx1=Math.max(bx1,b[j].x); by1=Math.max(by1,b[j].y);
      }
      var ix=Math.max(0,Math.min(ax1,bx1)-Math.max(ax0,bx0));
      var iy=Math.max(0,Math.min(ay1,by1)-Math.max(ay0,by0));
      var inter=ix*iy, ua=(ax1-ax0)*(ay1-ay0)+(bx1-bx0)*(by1-by0)-inter;
      return ua>0?inter/ua:0;
    }
    function ema(a,b,f){ var o=[],j;
      for(j=0;j<4;j++) o.push({x:a[j].x+(b[j].x-a[j].x)*f, y:a[j].y+(b[j].y-a[j].y)*f});
      return o; }
    if(best){
      if(!state.q){ state.q=best; state.score=bestS; state.lost=0; }
      else{
        var iou=boxIoU(best,state.q);
        if(iou>0.25){
          if(bestS>state.score*1.12){ state.q=ema(state.q,best,0.5); state.score=bestS; }
          else state.q=ema(state.q,best,0.18);
          state.lost=0;
        }else if(bestS>state.score*1.7){
          state.q=best; state.score=bestS; state.lost=0;
        }else state.lost=0;
      }
    }else{
      state.lost++;
      if(state.lost>8){ state.q=null; state.score=0; }
    }
    return {q:state.q, score:state.score, guide:!state.q};
  }
  function solve8(A,B){
    var n=8,M=[],i,c,r;
    for(i=0;i<n;i++){ M.push(A[i].slice()); M[i].push(B[i]); }
    for(c=0;c<n;c++){
      var piv=c;
      for(r=c+1;r<n;r++) if(Math.abs(M[r][c])>Math.abs(M[piv][c])) piv=r;
      var tmp=M[c]; M[c]=M[piv]; M[piv]=tmp;
      var d=M[c][c]||1e-9;
      for(r=0;r<n;r++){
        if(r===c) continue;
        var f=M[r][c]/d;
        for(var k=c;k<=n;k++) M[r][k]-=f*M[c][k];
      }
    }
    var x=[];
    for(i=0;i<n;i++) x.push(M[i][n]/(M[i][i]||1e-9));
    return x;
  }
  function inv3(m){
    var a=m[0][0],b=m[0][1],c=m[0][2],d=m[1][0],e=m[1][1],f=m[1][2],g=m[2][0],h=m[2][1],i=m[2][2];
    var A=e*i-f*h,B=-(d*i-f*g),C=d*h-e*g, det=a*A+b*B+c*C||1e-9;
    return [[A/det,(c*h-b*i)/det,(b*f-c*e)/det],
            [B/det,(a*i-c*g)/det,(c*d-a*f)/det],
            [C/det,(b*g-a*h)/det,(a*e-b*d)/det]];
  }
  function warp(px,w,h,quad,outW,outH){
    var dst=[{x:0,y:0},{x:outW,y:0},{x:outW,y:outH},{x:0,y:outH}],A=[],B=[];
    for(var i=0;i<4;i++){
      var sx=quad[i].x,sy=quad[i].y,dx=dst[i].x,dy=dst[i].y;
      A.push([sx,sy,1,0,0,0,-dx*sx,-dx*sy]); B.push(dx);
      A.push([0,0,0,sx,sy,1,-dy*sx,-dy*sy]); B.push(dy);
    }
    var H=solve8(A,B);
    var I=inv3([[H[0],H[1],H[2]],[H[3],H[4],H[5]],[H[6],H[7],1]]);
    /* Hot loop: direct indexing with inline edge clamping (no per-pixel
       function calls). At 300-DPI export sizes (~8MP) the old pxAt() version
       spent most of its time in 16M+ function calls; this is ~8x faster,
       which is what makes full-res export warps practical on phones. */
    var out=new Uint8ClampedArray(outW*outH*4);
    var w1=w-1, h1=h-1, w4=w*4;
    var i00=I[0][0],i01=I[0][1],i02=I[0][2],
        i10=I[1][0],i11=I[1][1],i12=I[1][2],
        i20=I[2][0],i21=I[2][1],i22=I[2][2];
    for(var y=0;y<outH;y++){
      var o=y*outW*4;
      for(var x=0;x<outW;x++,o+=4){
        var sxx=(i00*x+i01*y+i02)/(i20*x+i21*y+i22),
            syy=(i10*x+i11*y+i12)/(i20*x+i21*y+i22);
        var x0=sxx|0, y0=syy|0, fx=sxx-x0, fy=syy-y0;
        if(x0<0){x0=0;fx=0;}else if(x0>=w1){x0=w1-1;fx=1;}
        if(y0<0){y0=0;fy=0;}else if(y0>=h1){y0=h1-1;fy=1;}
        var p00=(y0*w+x0)*4, p10=p00+4, p01=p00+w4, p11=p01+4;
        var ba=(1-fx)*(1-fy), bb=fx*(1-fy), bc=(1-fx)*fy, bd=fx*fy;
        out[o]  =px[p00]*ba+px[p10]*bb+px[p01]*bc+px[p11]*bd;
        out[o+1]=px[p00+1]*ba+px[p10+1]*bb+px[p01+1]*bc+px[p11+1]*bd;
        out[o+2]=px[p00+2]*ba+px[p10+2]*bb+px[p01+2]*bc+px[p11+2]*bd;
        out[o+3]=px[p00+3]*ba+px[p10+3]*bb+px[p01+3]*bc+px[p11+3]*bd;
      }
    }
    return out;
  }
  /* Separable sliding-window box blur -> per-pixel local means, O(n) for any
     radius. Memory-light replacement for integral images: a Float64 integral
     at 300-DPI scan sizes costs 60-200MB+, this needs two Float32 buffers. */
  function boxBlurMean(f,w,h,R){
    var tmp=new Float32Array(w*h), out=new Float32Array(w*h), x, y, row;
    for(y=0;y<h;y++){ row=y*w;
      var lo=0, hi=-1, sum=0;
      for(x=0;x<w;x++){
        var nl=x-R>0?x-R:0, nr=x+R<w-1?x+R:w-1;
        while(lo<nl){ sum-=f[row+lo]; lo++; }
        while(hi<nr){ hi++; sum+=f[row+hi]; }
        tmp[row+x]=sum/(nr-nl+1);
      }
    }
    for(x=0;x<w;x++){
      var lo2=0, hi2=-1, sum2=0;
      for(y=0;y<h;y++){
        var nl2=y-R>0?y-R:0, nr2=y+R<h-1?y+R:h-1;
        while(lo2<nl2){ sum2-=tmp[lo2*w+x]; lo2++; }
        while(hi2<nr2){ hi2++; sum2+=tmp[hi2*w+x]; }
        out[y*w+x]=sum2/(nr2-nl2+1);
      }
    }
    return out;
  }
  function adaptiveBW(g,w,h){
    var n=w*h, mean=boxBlurMean(g,w,h,12);
    var out=new Uint8ClampedArray(n*4), i, o;
    for(i=0;i<n;i++){
      var v=g[i]<mean[i]*0.92?0:255; o=i*4;
      out[o]=out[o+1]=out[o+2]=v; out[o+3]=255;
    }
    return out;
  }
  /* "Magic"/Enhance done correctly: gray-world white balance FIRST (removes the
     yellow/green cast indoor phone photos pick up), THEN a gentle contrast
     stretch. The old version stretched contrast on the raw channels, which
     AMPLIFIED any cast instead of removing it. */
  function whiteBalanced(px,w,h){
    /* "Enhance": gray-world white balance, local-normalization flattening of
       uneven lighting (shadows), then percentile levels -> crisp black text
       on a clean white page, the CamScanner enhance look.
       Memory-light: one Float32 luminance buffer + one reusable mean/flat
       buffer (no Float64 integral image, no per-channel arrays), so 300-DPI
       exports don't blow the phone's memory. */
    var n=w*h,i,o;
    var mr=0,mg=0,mb=0;
    for(i=0;i<n;i++){ o=i*4; mr+=px[o]; mg+=px[o+1]; mb+=px[o+2]; }
    mr/=n; mg/=n; mb/=n;
    var g=(mr+mg+mb)/3;
    function cg(m){ var s=g/(m||1); return s<0.85?0.85:(s>1.18?1.18:s); }
    var sr=cg(mr),sg=cg(mg),sb=cg(mb);
    var lum=new Float32Array(n);
    for(i=0;i<n;i++){ o=i*4; lum[i]=(px[o]*sr+px[o+1]*sg+px[o+2]*sb)/3; }
    var R=Math.max(12,Math.round(Math.min(w,h)/24));
    var flat=boxBlurMean(lum,w,h,R); /* local mean, buffer reused as flattened values */
    for(i=0;i<n;i++){ flat[i]=lum[i]/Math.max(1,flat[i])*255; }
    lum=null;
    var hist=new Uint32Array(256),v;
    for(i=0;i<n;i++){ v=flat[i]|0; hist[v<0?0:(v>255?255:v)]++; }
    function pct(p){ var t=p*n,c=0; for(v=0;v<256;v++){ c+=hist[v]; if(c>=t) return v; } return 255; }
    var lo=pct(0.02),hi=pct(0.98),span=hi-lo;
    if(span<40){ lo=Math.max(0,hi-40); span=Math.max(1,hi-lo); }
    var out=new Uint8ClampedArray(n*4);
    for(i=0;i<n;i++){ o=i*4;
      var f=(flat[i]-lo)*255/span, L0=(px[o]*sr+px[o+1]*sg+px[o+2]*sb)/3||1;
      out[o]=f*(px[o]*sr/L0); out[o+1]=f*(px[o+1]*sg/L0); out[o+2]=f*(px[o+2]*sb/L0); out[o+3]=255;
    }
    return out;
  }
  function applyFilter(px,w,h,filter){
    if(filter==='bw') return adaptiveBW(gray(px,w,h),w,h);
    var out=new Uint8ClampedArray(px),i,o,c,v;
    if(filter==='gray'){
      var g=gray(px,w,h);
      for(i=0;i<w*h;i++){ v=g[i]|0; o=i*4; out[o]=out[o+1]=out[o+2]=v; }
      return out;
    }
    if(filter==='magic') return whiteBalanced(px,w,h);
    return out; /* 'color': natural, untouched */
  }
  return {detectQuad:detectQuad,detectLive:detectLive,guideRect:guideRect,warp:warp,applyFilter:applyFilter,gray:gray,
    refineCapture:refineCapture,quadArea:quadArea,
    /* QA/debug hook: scored candidate list for one live frame (not used by the app itself) */
    _dbgLive:function(px,w,h){ return scoreCandidates(px,w,h); },
    /* QA/debug hook: EVERY candidate incl. rejected ones, with fail reasons */
    _dbgAll:function(px,w,h){
      var g=gray(px,w,h), b=blurSep(g,w,h), sm=sobelXY(b,w,h);
      return searchQuads(sm,w,h,g,otsu(sm.m,w,h),true);
    },
    /* QA/debug: contour tracing diagnostics */
    _dbgContours:function(px,w,h){
      var g=gray(px,w,h), b=blurSep(g,w,h), sm=sobelXY(b,w,h), th=otsu(sm.m,w,h);
      var edge=new Uint8Array(w*h), ne=0;
      for(var i=0;i<w*h;i++){ if(sm.m[i]>th){ edge[i]=1; ne++; } }
      var cs=traceContours(edge,w,h);
      return { n:cs.length, info:cs.slice(0,10).map(function(c){
        var per=0,k;
        for(k=0;k<c.length;k++){ var a=c[k],bb=c[(k+1)%c.length];
          per+=Math.sqrt((a.x-bb.x)*(a.x-bb.x)+(a.y-bb.y)*(a.y-bb.y)); }
        return { len:c.length, per:Math.round(per), poly:approxClosed(c,per*0.02).length };
      })};
    }};
})();

/* ================= ENG: conversion engines ================= */
var ENG=(function(){
  function loadPdfDoc(bytes){
    return V.pdfjs().then(function(){
      /* slice: pdf.js transfers (neuters) the buffer to its worker — never hand
         it the caller's live bytes or later reuse sees a detached buffer. */
      return window.pdfjsLib.getDocument({data:bytes.slice(0)}).promise;
    });
  }
  function imagesToPdf(imgs){
    return V.pdfLib().then(function(){
      var PDFLib=window.PDFLib;
      return PDFLib.PDFDocument.create().then(function(doc){
        var chain=Promise.resolve();
        imgs.forEach(function(im){
          chain=chain.then(function(){
            var p=im.png?doc.embedPng(im.bytes):doc.embedJpg(im.bytes);
            return p.then(function(eimg){
              var page=doc.addPage([eimg.width,eimg.height]);
              page.drawImage(eimg,{x:0,y:0,width:eimg.width,height:eimg.height});
            });
          });
        });
        return chain.then(function(){ return doc.save(); });
      });
    });
  }
  function pdfToImages(bytes,scale,mime){
    return loadPdfDoc(bytes).then(function(doc){
      var out=[],chain=Promise.resolve();
      for(var i=1;i<=doc.numPages;i++)(function(pn){
        chain=chain.then(function(){ return doc.getPage(pn); }).then(function(page){
          var vp=page.getViewport({scale:scale||2});
          var cv=document.createElement('canvas');
          cv.width=Math.ceil(vp.width); cv.height=Math.ceil(vp.height);
          var ctx=cv.getContext('2d');
          return page.render({canvasContext:ctx,viewport:vp}).promise.then(function(){
            return new Promise(function(res,rej){
              cv.toBlob(function(b){
                if(!b){ rej(new Error('render')); return; }
                var fr=new FileReader();
                fr.onload=function(){ out.push(new Uint8Array(fr.result)); res(); };
                fr.onerror=function(){ rej(fr.error); };
                fr.readAsArrayBuffer(b);
              },mime||'image/png');
            });
          });
        });
      })(i);
      return chain.then(function(){ return out; });
    });
  }
  function pdfText(bytes){
    return loadPdfDoc(bytes).then(function(doc){
      var texts=[],chain=Promise.resolve();
      for(var i=1;i<=doc.numPages;i++)(function(pn){
        chain=chain.then(function(){ return doc.getPage(pn); })
          .then(function(pg){ return pg.getTextContent(); })
          .then(function(tc){
            var s='';
            (tc.items||[]).forEach(function(it){
              s+=it.str;
              if(it.hasEOL) s+='\n';
            });
            texts.push(s);
          });
      })(i);
      return chain.then(function(){ return texts; });
    });
  }
  /* raw text items per page (with style/position), for structured extraction */
  function pdfPageItems(bytes){
    return loadPdfDoc(bytes).then(function(doc){
      var n=doc.numPages, pages=[], chain=Promise.resolve();
      for(var i=1;i<=n;i++)(function(pn){
        chain=chain.then(function(){ return doc.getPage(pn); })
          .then(function(pg){ return pg.getTextContent().then(function(tc){
            pages.push({items:tc.items||[],styles:tc.styles||{}});
          }); });
      })(i);
      return chain.then(function(){ return pages; });
    });
  }
  /* Text-quality gate: refuse to build a .docx from scrambled/empty extraction.
     Broken custom-encoding PDFs (no valid ToUnicode) make pdf.js return raw
     glyph codes (substitution-cipher gibberish). We detect that by the share of
     extracted words that appear in a common-word list (en+es); gibberish scores ~0. */
  var WORDS={};
  ('the be to of and a in that have i it for not on with he as you do at this but his by from they we say her she or '+
   'an will my one all would there their what so up out if about who get which go me when make can like time no just him know take '+
   'people into year your good some could them see other than then now look only come its over think also back after use two how our '+
   'work first well way even new want because any these give day most us is are was were has had been are was were has had '+
   'el la de que y en un una los las se no por con una su para como esto esta son fue del al lo más pero sus le ya o este sí porque '+
   'esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese eso ante '+
   'ellos esto mí antes algunos qué unos les').split(' ').forEach(function(w){ WORDS[w]=1; });
  function textQuality(pages){
    var full='';
    pages.forEach(function(pg){
      (pg.items||[]).forEach(function(it){ full+=it.str+' '; });
    });
    var alpha=[];
    full.split(/\s+/).forEach(function(w){
      var c=String(w).toLowerCase().replace(/^[^a-zà-öø-ÿ]+|[^a-zà-öø-ÿ]+$/g,'');
      if(/^[a-zà-öø-ÿ]{2,}$/.test(c)) alpha.push(c);
    });
    if(alpha.length<15) return {ok:false,reason:'empty'};
    var hit=0;
    alpha.forEach(function(w){ if(WORDS[w]) hit++; });
    var ratio=hit/alpha.length;
    return {ok:ratio>=0.25,reason:ratio<0.25?'gibberish':'',ratio:ratio,words:alpha.length};
  }
  /* layout analysis: lines, reading order, body size (original) */
  function analyzePage(pg){
    var items=pg.items, styles=pg.styles, runs=[];
    items.forEach(function(it){
      if(!it.str||!it.str.length) return;
      var st=styles[it.fontName]||{};
      var fam=(st.fontFamily||'')+' '+(it.fontName||'');
      var h=it.height||Math.abs(it.transform[3])||10;
      runs.push({str:it.str,x:it.transform[4],y:it.transform[5],w:it.width||0,h:h,
        bold:/bold|black|heavy|demi/i.test(fam)});
    });
    if(!runs.length) return {lines:[],bodyH:12};
    var hs=runs.map(function(r){ return r.h; }).sort(function(a,b){ return a-b; });
    var bodyH=hs[Math.floor(hs.length/2)]||12;
    runs.sort(function(a,b){ return (b.y-a.y)||(a.x-b.x); });
    var lines=[], cur=null;
    runs.forEach(function(r){
      if(!cur||Math.abs(r.y-cur.y)>Math.max(r.h,cur.h)*0.55){
        cur={y:r.y,h:r.h,runs:[r],x0:r.x,x1:r.x+r.w};
        lines.push(cur);
      }else{
        cur.runs.push(r); cur.h=Math.max(cur.h,r.h);
        if(r.x<cur.x0) cur.x0=r.x;
        if(r.x+r.w>cur.x1) cur.x1=r.x+r.w;
      }
    });
    lines.forEach(function(ln){
      ln.runs.sort(function(a,b){ return a.x-b.x; });
      var tx='',prevEnd=null,chars=0,hsum=0;
      ln.runs.forEach(function(r){
        if(prevEnd!=null&&r.x-prevEnd>r.h*0.25) tx+=' ';
        tx+=r.str; prevEnd=r.x+r.w;
        var len=r.str.length; chars+=len; hsum+=r.h*len;
      });
      ln.text=tx.replace(/\s+/g,' ').trim();
      ln.avgH=chars?hsum/chars:ln.h;
    });
    return {lines:lines,bodyH:bodyH};
  }
  /* ---- FLAGSHIP: structure-aware PDF -> Word ----
     Headings (by size), bulleted/numbered/lettered lists, simple tables
     (column-aligned runs) rebuilt as real Word structure via the docx lib.
     Paragraphs merged by line spacing, reading order per page, page breaks
     between PDF pages. Honest label stays: complex layouts may simplify. */
  function pdfToWord(bytes){
    return pdfPageItems(bytes).then(function(pages){
      /* honest gate: never ship a garbage .docx from scrambled/empty text */
      var q=textQuality(pages);
      if(!q.ok){ var e=new Error('pdf-text-unreadable'); e.code='BADTEXT'; e.reason=q.reason; throw e; }
      return V.docx().then(function(){
        var D=window.docx;
        /* NOTE: this docx build's File constructor wraps options.numbering in
           `new Numbering(...)` itself, so pass the raw {config:[...]} object. */
        var numberingCfg={config:[
          {reference:'sc-bullet',levels:[{level:0,format:D.LevelFormat.BULLET,text:'\u2022',
            alignment:D.AlignmentType.LEFT,
            style:{paragraph:{indent:{left:720,hanging:360}}}}]},
          {reference:'sc-decimal',levels:[{level:0,format:D.LevelFormat.DECIMAL,text:'%1.',
            alignment:D.AlignmentType.LEFT,
            style:{paragraph:{indent:{left:720,hanging:360}}}}]},
          {reference:'sc-letter',levels:[{level:0,format:D.LevelFormat.LOWER_LETTER,text:'%1)',
            alignment:D.AlignmentType.LEFT,
            style:{paragraph:{indent:{left:720,hanging:360}}}}]}
        ]};
        var BULLET_RE=/^\s*(?:\u2022|\u25e6|\u25aa|\u25b8|\u00b7|-|\*|\u2013|\u2014)\s+/;
        var DEC_RE=/^\s*\d{1,3}[.)]\s+/;
        var LET_RE=/^\s*[a-zA-Z][.)]\s+/;
        function textRuns(ln,stripRe){
          var groups=[],prevEnd=null;
          ln.runs.forEach(function(r){
            var s=r.str;
            if(stripRe&&groups.length===0){
              s=s.replace(stripRe,'');
              if(!s){ prevEnd=r.x+r.w; return; }
            }
            var needSpace=prevEnd!=null&&(r.x-prevEnd>r.h*0.25);
            var last=groups[groups.length-1];
            if(last&&last.bold===r.bold){ last.text+=(needSpace?' ':'')+s; }
            else groups.push({bold:r.bold,text:(needSpace?' ':'')+s});
            prevEnd=r.x+r.w;
          });
          return groups.map(function(g){
            return new D.TextRun({text:g.text,bold:g.bold?true:undefined});
          });
        }
        function gapThresh(bodyH){ return Math.max(10,bodyH*1.1); }
        function cruns(ln){ return ln.runs.filter(function(r){ return r.str.trim().length>0; }); }
        function bigGaps(ln,bodyH){
          var cr=cruns(ln), n=0, th=gapThresh(bodyH);
          for(var i=1;i<cr.length;i++)
            if(cr[i].x-(cr[i-1].x+cr[i-1].w)>th) n++;
          return n;
        }
        var children=[];
        pages.forEach(function(pg,pi){
          var an=analyzePage(pg), lines=an.lines, bodyH=an.bodyH;
          lines.forEach(function(ln){
            ln.kind='p'; ln.tblId=-1;
            if(ln.text.length<140){
              var ratio=ln.avgH/bodyH;
              if(ratio>=1.65) ln.kind='h1';
              else if(ratio>=1.4) ln.kind='h2';
              else if(ratio>=1.22) ln.kind='h3';
            }
            if(ln.kind==='p'){
              if(BULLET_RE.test(ln.text)) ln.kind='bul';
              else if(DEC_RE.test(ln.text)) ln.kind='dec';
              else if(LET_RE.test(ln.text)) ln.kind='let';
            }
          });
          /* table blocks: consecutive paragraph lines with column gaps */
          var tblSeq=0,i;
          for(i=0;i<lines.length;){
            if(lines[i].kind!=='p'||bigGaps(lines[i],bodyH)<1){ i++; continue; }
            var j=i;
            while(j<lines.length&&lines[j].kind==='p'&&bigGaps(lines[j],bodyH)>=1) j++;
            if(j-i>=2){ for(var k=i;k<j;k++){ lines[k].kind='tbl'; lines[k].tblId=tblSeq; } tblSeq++; }
            i=j;
          }
          var bid=0;
          while(bid<lines.length){
            var L=lines[bid];
            if(L.kind==='tbl'){
              var rows=[],tid=L.tblId;
              while(bid<lines.length&&lines[bid].kind==='tbl'&&lines[bid].tblId===tid){ rows.push(lines[bid]); bid++; }
              var xs=[];
              rows.forEach(function(r){ cruns(r).forEach(function(run){ xs.push(run.x); }); });
              xs.sort(function(a,b){ return a-b; });
              var cols=[];
              xs.forEach(function(x){
                var last=cols[cols.length-1];
                if(last!=null&&x-last<10) cols[cols.length-1]=(last+x)/2;
                else cols.push(x);
              });
              if(cols.length>=2){
                var trows=rows.map(function(r){
                  var cells=cols.map(function(){ return []; });
                  cruns(r).forEach(function(run){
                    var bi2=0,bd=Infinity;
                    cols.forEach(function(cx,ci){ var d=Math.abs(run.x-cx); if(d<bd){ bd=d; bi2=ci; } });
                    cells[bi2].push(run);
                  });
                  return new D.TableRow({children:cells.map(function(cellRuns){
                    return new D.TableCell({children:[new D.Paragraph({children:textRuns({runs:cellRuns,h:bodyH})})]});
                  })});
                });
                children.push(new D.Table({width:{size:100,type:D.WidthType.PERCENTAGE},rows:trows}));
              }else{
                rows.forEach(function(r){ children.push(new D.Paragraph({children:textRuns(r)})); });
              }
              continue;
            }
            if(L.kind==='p'){
              var merged={runs:L.runs.slice(),h:bodyH,y:L.y};
              bid++;
              while(bid<lines.length&&lines[bid].kind==='p'&&(merged.y-lines[bid].y)<bodyH*1.7){
                merged.runs=merged.runs.concat(lines[bid].runs);
                merged.y=lines[bid].y; bid++;
              }
              children.push(new D.Paragraph({children:textRuns(merged)}));
              continue;
            }
            if(L.kind==='bul'||L.kind==='dec'||L.kind==='let'){
              var ref=L.kind==='bul'?'sc-bullet':(L.kind==='dec'?'sc-decimal':'sc-letter');
              var mre=L.kind==='bul'?BULLET_RE:(L.kind==='dec'?DEC_RE:LET_RE);
              children.push(new D.Paragraph({numbering:{reference:ref,level:0},children:textRuns(L,mre)}));
            }else{
              var hl=L.kind==='h1'?D.HeadingLevel.HEADING_1
                   :L.kind==='h2'?D.HeadingLevel.HEADING_2:D.HeadingLevel.HEADING_3;
              children.push(new D.Paragraph({heading:hl,children:textRuns(L)}));
            }
            bid++;
          }
          if(pi<pages.length-1)
            children.push(new D.Paragraph({children:[new D.PageBreak()]}));
        });
        if(!children.length) children.push(new D.Paragraph(' '));
        var doc=new D.Document({numbering:numberingCfg,sections:[{children:children}]});
        return D.Packer.toBlob(doc);
      });
    });
  }

  function wordToHtml(bytes){
    return V.mammoth().then(function(){
      return window.mammoth.convertToHtml({arrayBuffer:bytes.buffer});
    }).then(function(r){ return r.value||''; });
  }
  function mergePdfs(list){
    return V.pdfLib().then(function(){
      var PDFLib=window.PDFLib;
      return PDFLib.PDFDocument.create().then(function(doc){
        var chain=Promise.resolve();
        list.forEach(function(bytes){
          chain=chain.then(function(){ return PDFLib.PDFDocument.load(bytes); })
            .then(function(src){
              return doc.copyPages(src,src.getPageIndices()).then(function(cps){
                cps.forEach(function(cp){ doc.addPage(cp); });
              });
            });
        });
        return chain.then(function(){ return doc.save(); });
      });
    });
  }
  /* "1-3,5" -> [1,2,3,5] (1-based, clamped, deduped) */
  function parseRanges(str,n){
    var out=[];
    String(str||'').split(',').forEach(function(part){
      part=part.trim(); if(!part) return;
      var m=part.match(/^(\d+)\s*-\s*(\d+)$/);
      if(m){
        var a=parseInt(m[1],10), b=parseInt(m[2],10), tmp;
        if(a>b){ tmp=a; a=b; b=tmp; }
        for(var i=a;i<=b;i++) if(i>=1&&i<=n&&out.indexOf(i)<0) out.push(i);
      }else{
        var p=parseInt(part,10);
        if(p>=1&&p<=n&&out.indexOf(p)<0) out.push(p);
      }
    });
    return out;
  }
  function splitPdf(bytes,rangeList){
    return V.pdfLib().then(function(){
      var PDFLib=window.PDFLib;
      return PDFLib.PDFDocument.load(bytes).then(function(src){
        var chain=Promise.resolve(), outs=[];
        rangeList.forEach(function(pages){
          chain=chain.then(function(){
            return PDFLib.PDFDocument.create().then(function(doc){
              return doc.copyPages(src,pages.map(function(p){ return p-1; })).then(function(cps){
                cps.forEach(function(cp){ doc.addPage(cp); });
                return doc.save().then(function(b){ outs.push(b); });
              });
            });
          });
        });
        return chain.then(function(){ return outs; });
      });
    });
  }
  function rotatePdf(bytes,deg){
    return V.pdfLib().then(function(){
      var PDFLib=window.PDFLib;
      return PDFLib.PDFDocument.load(bytes).then(function(doc){
        doc.getPages().forEach(function(p){
          p.setRotation(PDFLib.degrees((p.getRotation().angle+deg)%360));
        });
        return doc.save();
      });
    });
  }
  function reorderPdf(bytes,order){
    return V.pdfLib().then(function(){
      var PDFLib=window.PDFLib;
      return PDFLib.PDFDocument.load(bytes).then(function(src){
        return PDFLib.PDFDocument.create().then(function(doc){
          return doc.copyPages(src,order.map(function(p){ return p-1; })).then(function(cps){
            cps.forEach(function(cp){ doc.addPage(cp); });
            return doc.save();
          });
        });
      });
    });
  }
  function compressPdf(bytes,quality){
    return loadPdfDoc(bytes).then(function(doc){
      var n=doc.numPages, imgs=[], chain=Promise.resolve();
      for(var i=1;i<=n;i++)(function(pn){
        chain=chain.then(function(){ return doc.getPage(pn); }).then(function(page){
          var vp=page.getViewport({scale:1.5});
          var cv=document.createElement('canvas');
          cv.width=Math.ceil(vp.width); cv.height=Math.ceil(vp.height);
          var ctx=cv.getContext('2d');
          ctx.fillStyle='#ffffff'; ctx.fillRect(0,0,cv.width,cv.height);
          return page.render({canvasContext:ctx,viewport:vp}).promise.then(function(){
            return new Promise(function(res,rej){
              cv.toBlob(function(b){
                if(!b){ rej(new Error('render')); return; }
                var fr=new FileReader();
                fr.onload=function(){ imgs.push({bytes:new Uint8Array(fr.result),png:false}); res(); };
                fr.onerror=function(){ rej(fr.error); };
                fr.readAsArrayBuffer(b);
              },'image/jpeg',quality||0.6);
            });
          });
        });
      })(i);
      return chain.then(function(){ return imagesToPdf(imgs); });
    });
  }
  function pdfToExcel(bytes){
    return V.xlsx().then(function(){
      return pdfText(bytes).then(function(texts){
        var XLSX=window.XLSX, wb=XLSX.utils.book_new();
        texts.forEach(function(tx,i){
          var rows=tx.split('\n').map(function(ln){ return [ln]; });
          XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet(rows.length?rows:[['']]),'Page '+(i+1));
        });
        return XLSX.write(wb,{bookType:'xlsx',type:'array'});
      });
    });
  }
  function convertImage(bytes,mime,q){
    return new Promise(function(res,rej){
      var url=URL.createObjectURL(blobOf(bytes));
      var img=new Image();
      img.onload=function(){
        URL.revokeObjectURL(url);
        var cv=document.createElement('canvas');
        cv.width=img.naturalWidth; cv.height=img.naturalHeight;
        cv.getContext('2d').drawImage(img,0,0);
        cv.toBlob(function(b){
          if(!b){ rej(new Error('conv')); return; }
          var fr=new FileReader();
          fr.onload=function(){ res({bytes:new Uint8Array(fr.result),mime:mime}); };
          fr.onerror=function(){ rej(fr.error); };
          fr.readAsArrayBuffer(b);
        },mime,q);
      };
      img.onerror=function(){ URL.revokeObjectURL(url); rej(new Error('imgload')); };
      img.src=url;
    });
  }
  function heicToJpg(bytes){
    return V.heic().then(function(){
      return window.heic2any({blob:blobOf(bytes,'image/heic'),toType:'image/jpeg',quality:0.92});
    }).then(function(out){
      var blob=Array.isArray(out)?out[0]:out;
      return new Promise(function(res,rej){
        var fr=new FileReader();
        fr.onload=function(){ res(new Uint8Array(fr.result)); };
        fr.onerror=function(){ rej(fr.error); };
        fr.readAsArrayBuffer(blob);
      });
    });
  }
  /* multi-page scan -> Word: each scanned page embedded as an image, one per page.
     Honest by design: scanned pages are pictures, so the text is NOT editable. */
  function scanToDocx(pages){
    return V.docx().then(function(){
      var D=window.docx;
      var children=[], chain=Promise.resolve();
      pages.forEach(function(p,i){
        chain=chain.then(function(){ return canvasJpg(p.cv,0.85); }).then(function(jpg){
          var w=560, h=Math.round(w*p.cv.height/Math.max(1,p.cv.width));
          children.push(new D.Paragraph({children:[
            new D.ImageRun({data:jpg,transformation:{width:w,height:h}})
          ]}));
          if(i<pages.length-1) children.push(new D.Paragraph({children:[new D.PageBreak()]}));
        });
      });
      return chain.then(function(){
        var doc=new D.Document({sections:[{children:children}]});
        return D.Packer.toBlob(doc);
      });
    });
  }
  return {
    loadPdfDoc:loadPdfDoc, imagesToPdf:imagesToPdf, pdfToImages:pdfToImages,
    pdfText:pdfText, pdfPageItems:pdfPageItems, analyzePage:analyzePage, pdfToWord:pdfToWord,
    wordToHtml:wordToHtml, mergePdfs:mergePdfs, parseRanges:parseRanges, splitPdf:splitPdf,
    rotatePdf:rotatePdf, reorderPdf:reorderPdf, compressPdf:compressPdf,
    pdfToExcel:pdfToExcel, convertImage:convertImage, heicToJpg:heicToJpg, scanToDocx:scanToDocx
  };
})();

/* ================= tool registry: 14 tools, 4 labeled sections ================= */
var TOOLS=[
  {id:'scan',sec:'create',title:'scan.tScan',desc:'scan.dScan',pick:'none',icon:'scan-doc'},
  {id:'photos2pdf',icon:'scan-doc',sec:'create',title:'scan.tPhotos2pdf',desc:'scan.dPhotos2pdf',pick:'scan.pickImage',accept:'image/*',multi:true},
  {id:'pdf2word',icon:'scan-doc',sec:'convert',title:'scan.tPdf2word',desc:'scan.dPdf2word',note:'scan.pdf2wordNote',pick:'scan.pickPdf',accept:'application/pdf',multi:false},
  {id:'word2pdf',icon:'scan-doc',sec:'convert',title:'scan.tWord2pdf',desc:'scan.dWord2pdf',note:'scan.word2pdfNote',pick:'scan.pickWord',accept:'.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document',multi:false},
  {id:'pdf2img',icon:'scan-doc',sec:'convert',title:'scan.tPdf2img',desc:'scan.dPdf2img',pick:'scan.pickPdf',accept:'application/pdf',multi:false},
  {id:'pdf2text',icon:'scan-doc',sec:'convert',title:'scan.tPdf2text',desc:'scan.dPdf2text',pick:'scan.pickPdf',accept:'application/pdf',multi:false},
  {id:'pdf2excel',icon:'scan-doc',sec:'convert',title:'scan.tPdf2excel',desc:'scan.dPdf2excel',note:'scan.pdf2excelNote',pick:'scan.pickPdf',accept:'application/pdf',multi:false},
  {id:'imgconv',icon:'scan-doc',sec:'convert',title:'scan.tImgconv',desc:'scan.dImgconv',pick:'scan.pickImage',accept:'image/*',multi:false},
  {id:'heic2jpg',icon:'scan-doc',sec:'convert',title:'scan.tHeic2jpg',desc:'scan.dHeic2jpg',note:'scan.heicNote',pick:'scan.pickHeic',accept:'image/heic,image/heif,.heic,.heif',multi:false},
  {id:'merge',icon:'scan-doc',sec:'organize',title:'scan.tMerge',desc:'scan.dMerge',pick:'scan.pickPdf',accept:'application/pdf',multi:true},
  {id:'split',icon:'scan-doc',sec:'organize',title:'scan.tSplit',desc:'scan.dSplit',pick:'scan.pickPdf',accept:'application/pdf',multi:false},
  {id:'rotate',icon:'scan-doc',sec:'organize',title:'scan.tRotate',desc:'scan.dRotate',pick:'scan.pickPdf',accept:'application/pdf',multi:false},
  {id:'reorder',icon:'scan-doc',sec:'organize',title:'scan.tReorder',desc:'scan.dReorder',pick:'scan.pickPdf',accept:'application/pdf',multi:false},
  {id:'compress',icon:'scan-doc',sec:'compress',title:'scan.tCompress',desc:'scan.dCompress',pick:'scan.pickPdf',accept:'application/pdf',multi:false}
];
var SECTIONS=['create','convert','organize','compress'];

/* ================= R: overlay shell + shared render helpers ================= */
function closeScanOverlay(){ var h=$('.scroot'); if(h) h.remove(); }
var R={
  overlay:function(title){
    closeScanOverlay();
    var host=document.createElement('div');
    host.className='chatroot scroot';
    host.innerHTML='<div class="sc-sheet" role="dialog" aria-label="'+esc(title)+'">'+
      '<div class="sc-topbar"><button class="sc-x" data-close aria-label="'+esc(t('scan.close'))+'">✕</button>'+
      '<div class="sc-title">'+esc(title)+'</div><div class="sc-xsp"></div></div>'+
      '<div class="sc-body"></div></div>';
    document.body.appendChild(host);
    host.querySelector('[data-close]').onclick=closeScanOverlay;
    host.addEventListener('mousedown',function(e){ if(e.target===host) closeScanOverlay(); });
    return host;
  },
  busy:function(body,on){
    var b=$('.sc-busy',body);
    if(on&&!b) body.appendChild(el('<div class="sc-busy"><div class="sc-spin"></div><div>'+esc(t('scan.working'))+'</div></div>'));
    if(!on&&b) b.remove();
  },
  err:function(body){
    if(ui.toast) ui.toast(t('scan.failed'));
    body.appendChild(el('<div class="sc-note sc-err">'+esc(t('scan.failed'))+'</div>'));
  },
  done:function(body,icon,title,bytes,filename,mime){
    var blob=bytes instanceof Blob?bytes:blobOf(bytes,mime);
    var url=URL.createObjectURL(blob);
    var d=el('<div class="sc-done"><div class="sc-doneic">'+icon+'</div>'+
      '<div class="sc-donetitle">'+esc(title)+'</div>'+
      '<div class="sc-donefn">'+esc(filename)+'</div>'+
      '<div class="sc-row"><button class="sc-btn sc-primary" data-share>'+esc(t('scan.share'))+'</button>'+
      '<button class="sc-btn" data-dl>'+esc(t('scan.download'))+'</button>'+
      ((/^(image|application\/pdf)/).test(blob.type)?'<button class="sc-btn" data-view>'+esc(t('scan.view'))+'</button>':'')+
      '</div></div>');
    body.appendChild(d);
    d.querySelector('[data-share]').onclick=function(){ shareOrDownload(blob,filename,title); };
    d.querySelector('[data-dl]').onclick=function(){ downloadBlob(blob,filename); };
    var vv=d.querySelector('[data-view]');
    if(vv) vv.onclick=function(){ window.open(url,'_blank'); };
  },
  /* multi-file result card: share all files together when the platform
     allows it, otherwise one download button per file */
  doneMulti:function(body,icon,title,files){
    var d=el('<div class="sc-done"><div class="sc-doneic">'+icon+'</div>'+
      '<div class="sc-donetitle">'+esc(title)+'</div>'+
      '<div class="sc-donefn">'+files.map(function(f){ return esc(f.name); }).join('<br>')+'</div>'+
      '<div class="sc-row"><button class="sc-btn sc-primary" data-share>'+esc(t('scan.share'))+'</button></div>'+
      '<div class="sc-col" data-dls></div></div>');
    body.appendChild(d);
    var blobs=files.map(function(f){ return blobOf(f.bytes,f.mime); });
    var dlHost=d.querySelector('[data-dls]');
    blobs.forEach(function(b,i){
      var btn=el('<button class="sc-btn sc-wide">'+esc(t('scan.download'))+' · '+esc(files[i].name)+'</button>');
      btn.onclick=(function(bb,fn){ return function(){ downloadBlob(bb,fn); }; })(b,files[i].name);
      dlHost.appendChild(btn);
    });
    var shareBtn=d.querySelector('[data-share]'), ok=false;
    try{
      var fs=blobs.map(function(b,i){ return new File([b],files[i].name,{type:b.type}); });
      if(navigator.canShare&&navigator.canShare({files:fs})){
        ok=true;
        shareBtn.onclick=function(){ navigator.share({files:fs,title:title}).catch(function(){}); };
      }
    }catch(e){ ok=false; }
    if(!ok) shareBtn.style.display='none';
  },
  pick:function(body,labelKey,accept,multi,cb){
    var w=el('<div class="sc-pick"><div class="sc-note">'+esc(t(labelKey))+'</div>'+
      '<button class="sc-btn sc-wide">'+esc(t('scan.chooseFiles'))+'</button>'+
      '<input type="file" accept="'+esc(accept||'')+'"'+(multi?' multiple':'')+' hidden></div>');
    body.appendChild(w);
    var inp=w.querySelector('input');
    w.querySelector('button').onclick=function(){
      /* iOS Safari ignores file-input clicks outside the direct tap handler:
         click synchronously, nudge (one-time explainer) fire-and-forget. */
      inp.click();
      if(HUB.perms) HUB.perms.nudge('photos');
    };
    inp.onchange=function(){
      var files=Array.prototype.slice.call(inp.files||[]);
      if(!files.length) return;
      w.remove(); R.busy(body,true);
      var chain=Promise.resolve(), out=[];
      files.forEach(function(f){
        chain=chain.then(function(){ return fileBytes(f); }).then(function(b){
          out.push({name:f.name,bytes:b,mime:f.type||'application/octet-stream'});
        });
      });
      chain.then(function(){ R.busy(body,false); refreshCount(); cb(out); },
        function(){ R.busy(body,false); R.err(body); });
    };
  },
  saveFiles:function(files){
    var chain=Promise.resolve();
    files.forEach(function(f){
      chain=chain.then(function(){
        return DB.add({name:f.name,mime:f.mime,bytes:f.bytes,ts:Date.now()});
      });
    });
    return chain.then(function(){ refreshCount(); });
  },
  nm:function(name,suffix){
    return String(name||'file').replace(/\.[^.]+$/,'')+suffix;
  },
  home:function(host){
    var body=host.querySelector('.sc-body');
    var html='<div class="sc-note">'+esc(t('scan.studioNote'))+'</div>';
    SECTIONS.forEach(function(sec){
      html+='<div class="sc-sect">'+esc(t('scan.sec_'+sec))+'</div><div class="sc-grid">';
      TOOLS.forEach(function(tl){
        if(tl.sec!==sec) return;
        html+='<button class="sc-tile" data-tool="'+tl.id+'">'+
          '<span class="sc-tile-ic">'+scIcon(tl.icon)+'</span>'+
          '<span class="sc-tiletx">'+esc(t(tl.title))+'</span>'+
          '<span class="sc-tiledesc">'+esc(t(tl.desc))+'</span>'+
          (tl.note?'<span class="sc-tilenote">'+esc(t(tl.note))+'</span>':'')+'</button>';
      });
      html+='</div>';
    });
    html+='<div class="sc-sect">'+esc(t('scan.sec_files'))+'</div><div class="sc-files" data-files></div>';
    body.innerHTML=html;
    body.querySelectorAll('[data-tool]').forEach(function(b){
      b.onclick=function(){ HUB.scan.tool(b.getAttribute('data-tool')); };
    });
    R.fileList(body);
  },
  fileList:function(body){
    var box=body.querySelector('[data-files]');
    if(!box) return;
    DB.all().then(function(recs){
      recs=(recs||[]).sort(function(a,b){ return b.ts-a.ts; });
      if(!recs.length){ box.innerHTML='<div class="sc-note">'+esc(t('scan.noFiles'))+'</div>'; return; }
      box.innerHTML='';
      recs.forEach(function(r){
        var d=el('<div class="sc-filerow"><div class="sc-filemeta"><div class="sc-filename">'+esc(r.name)+'</div>'+
          '<div class="sc-filets">'+new Date(r.ts).toLocaleString()+'</div></div>'+
          '<button class="sc-btn" data-share>'+esc(t('scan.share'))+'</button>'+
          '<button class="sc-btn" data-del>'+esc(t('scan.delete'))+'</button></div>');
        d.querySelector('[data-share]').onclick=function(){
          shareOrDownload(blobOf(r.bytes,r.mime),r.name,r.name);
        };
        d.querySelector('[data-del]').onclick=function(){
          DB.del(r.id).then(function(){ R.fileList(body); refreshCount(); });
        };
        box.appendChild(d);
      });
    }).catch(function(){ box.innerHTML='<div class="sc-note">'+esc(t('scan.noFiles'))+'</div>'; });
  }
};

/* ================= SCAN flow: capture -> crop -> pages -> PDF ================= */
var SCAN={
  pages:[],
  _capHook:null, /* optional capture redirect: retake-in-place / append-to-session */
  /* one review-session item: source canvas + quad + filter/size + warp cache */
  _mkItem:function(cv,qq){
    var W=cv.width,H=cv.height;
    return {cv:cv,W:W,H:H,
      srcPx:cv.getContext('2d').getImageData(0,0,W,H).data,
      q:(qq&&qq.length===4)?qq.map(function(p){ return {x:p.x,y:p.y}; }):SCAN.detectQuad(cv),
      filter:'color',size:'auto',pgRef:-1,
      cache:{key:null,imgs:null,w:0,h:0}};
  },
  start:function(body,keep){
    if(!keep) SCAN.pages=[];
    body.innerHTML='<div class="sc-note">'+esc(t('scan.scanHow'))+'</div>'+
      '<div class="sc-col">'+
      '<button class="sc-btn sc-wide" data-m="take">📷 '+esc(t('scan.takePhoto'))+'</button>'+
      '<button class="sc-btn sc-wide" data-m="choose">🖼️ '+esc(t('scan.chooseLib'))+'</button>'+
      '<button class="sc-btn sc-wide" data-m="upload">📁 '+esc(t('scan.uploadFile'))+'</button></div>'+
      '<input type="file" accept="image/*" capture="environment" hidden data-take>'+
      '<input type="file" accept="image/*" multiple hidden data-choose>';
    var take=body.querySelector('[data-take]'), choose=body.querySelector('[data-choose]');
    function handle(files){
      var list=Array.prototype.slice.call(files||[]);
      if(!list.length) return; /* picker cancelled: stay on screen, no dead end */
      R.busy(body,true);
      var chain=Promise.resolve(), added=0, failed=0;
      list.forEach(function(f,i){
        chain=chain.then(function(){ return fileBytes(f); })
          .then(function(b){ return loadImage(b); })
          .then(function(img){ return imgToCanvas(img,3000); })
          .then(function(srcCv){
            if(list.length===1){ R.busy(body,false); SCAN.cropView(body,srcCv); }
            else{
              /* multi-pick: auto-crop each with the detected quad, no per-file stop */
              var q=SCAN.detectQuad(srcCv);
              SCAN.pages.push({cv:SCAN.makePage(srcCv,q,'color','auto'),filter:'color'});
              added++;
            }
          })
          .catch(function(){ failed++; });
      });
      chain.then(function(){
        R.busy(body,false);
        if(list.length>1||added>0){
          if(!SCAN.pages.length){ SCAN.start(body,true);
            body.insertBefore(el('<div class="sc-note sc-err">'+esc(t('scan.imgFailed'))+'</div>'),body.firstChild);
          }else SCAN.pagesView(body);
        }else if(failed){
          R.err(body);
          body.insertBefore(el('<div class="sc-note sc-err">'+esc(t('scan.imgFailed'))+'</div>'),body.firstChild);
        }
      });
    }
    /* NOTE: file inputs must be clicked synchronously inside the tap handler —
       iOS Safari silently drops async input.click() calls (no picker, no error).
       Permission explainers go through nudge(): one-time, non-blocking. */
    var gateTake=function(){
      if(body.querySelector('.sc-camwrap')) return; /* camView already open: ignore re-entry */
      if(HUB.perms) HUB.perms.nudge('camera');
      if(!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)){ take.click(); return; } /* legacy native-camera fallback */
      SCAN.camView(body);
    };
    var gateChoose=function(){
      choose.click();
      if(HUB.perms) HUB.perms.nudge('photos');
    };
    body.querySelector('[data-m="take"]').onclick=gateTake;
    body.querySelector('[data-m="choose"]').onclick=gateChoose;
    body.querySelector('[data-m="upload"]').onclick=gateChoose;
    take.onchange=function(){ handle(take.files); take.value=''; };
    choose.onchange=function(){ handle(choose.files); choose.value=''; };
  },
  /* edge detection on a small copy for speed, quad scaled back to full size.
     Hardened: hough sometimes returns out-of-bounds/degenerate quads (e.g. a photo
     with no clear document edges) which used to warp into a silent black page.
     Clamp into the image and fall back to a full-bleed inset rect when degenerate. */
  detectQuad:function(srcCv){
    var w=srcCv.width,h=srcCv.height;
    var ds=Math.min(1,400/Math.max(w,h));
    var dw=Math.max(1,Math.round(w*ds)), dh=Math.max(1,Math.round(h*ds));
    var dcv=document.createElement('canvas');
    var dctx=dcv.getContext('2d'); dctx.drawImage(srcCv,0,0,dw,dh);
    var dpx=dctx.getImageData(0,0,dw,dh).data;
    function inset(){ var mx=w*0.04,my=h*0.04;
      return [{x:mx,y:my},{x:w-mx,y:my},{x:w-mx,y:h-my},{x:mx,y:h-my}]; }
    var q;
    try{ q=CV.detectQuad(dpx,dw,dh).map(function(p){ return {x:p.x/ds,y:p.y/ds}; }); }
    catch(e){ return inset(); }
    if(!q||q.length!==4) return inset();
    q=q.map(function(p){ return {x:Math.min(w,Math.max(0,p.x)), y:Math.min(h,Math.max(0,p.y))}; });
    var area=0,i;
    for(i=0;i<4;i++){ var a=q[i],b=q[(i+1)%4]; area+=a.x*b.y-b.x*a.y; }
    if(Math.abs(area)/2<w*h*0.05) return inset();
    return q;
  },
  /* perspective-crop + filter -> finished page canvas.
     sizeKey: 'auto' (detected aspect) | 'a4' | 'letter' | 'legal'.
     outW: optional explicit long-edge override (default: ~300-DPI auto). */
  pageAspect:function(q,sizeKey){
    if(sizeKey==='a4') return 210/297;
    if(sizeKey==='letter') return 8.5/11;
    if(sizeKey==='legal') return 8.5/14;
    var topE=Math.hypot(q[1].x-q[0].x,q[1].y-q[0].y), botE=Math.hypot(q[2].x-q[3].x,q[2].y-q[3].y);
    var lE=Math.hypot(q[3].x-q[0].x,q[3].y-q[0].y), rE=Math.hypot(q[2].x-q[1].x,q[2].y-q[1].y);
    return Math.max(topE,botE)/Math.max(1,Math.max(lE,rE));
  },
  /* Export render size: ~300 DPI on the long edge (Letter/A4 -> ~3300px) so
     pinch-zoom reveals real detail. Never upscale beyond 1.25x the paper
     pixels actually captured (no fake detail); never below 1800px long edge. */
  pageDims:function(q,sizeKey){
    var asp=SCAN.pageAspect(q,sizeKey||'auto'), e=0, i;
    for(i=0;i<4;i++){ var j=(i+1)%4;
      e=Math.max(e,Math.hypot(q[j].x-q[i].x,q[j].y-q[i].y)); }
    var LONG=Math.min(3300,Math.max(1800,Math.round(e*1.25)));
    var w,h;
    if(asp>=1){ w=LONG; h=Math.max(1,Math.round(LONG/asp)); }
    else { h=LONG; w=Math.max(1,Math.round(LONG*asp)); }
    return [w,h];
  },
  /* High-quality thumbnail: step down in halvings instead of one giant
     drawImage downscale. A single 12x downscale (e.g. 1941px page -> 160px
     thumbnail) aliases dense document lines into wavy dashed moire wavefronts
     and dark blotches; halvings stay well-filtered at every step. */
  _thumb:function(srcCv,targetW){
    var w=srcCv.width,h=srcCv.height;
    if(!w||!h) return srcCv;
    var tw=Math.min(targetW,w), th=Math.max(1,Math.round(h*tw/w));
    var src=srcCv, cw=w, ch=h;
    while(cw>tw*2){
      var nw=Math.max(1,Math.round(cw/2)), nh=Math.max(1,Math.round(ch/2));
      var t=document.createElement('canvas'); t.width=nw; t.height=nh;
      t.getContext('2d').drawImage(src,0,0,nw,nh);
      src=t; cw=nw; ch=nh;
    }
    var c=document.createElement('canvas'); c.width=tw; c.height=th;
    c.getContext('2d').drawImage(src,0,0,tw,th);
    return c;
  },
  makePage:function(srcCv,q,filter,sizeKey,outW){
    var asp=SCAN.pageAspect(q,sizeKey||'auto');
    function dimsFor(longEdge){
      var w,h;
      if(asp>=1){ w=longEdge; h=Math.max(1,Math.round(longEdge/asp)); }
      else { h=longEdge; w=Math.max(1,Math.round(longEdge*asp)); }
      return [w,h];
    }
    /* Tiered render: try full 300-DPI first, step down only if the device
       can't hold it (allocation throws). Never a silent tiny output. */
    var tiers;
    if(outW){ tiers=[dimsFor(outW)]; }
    else{
      var d0=SCAN.pageDims(q,sizeKey||'auto');
      tiers=[d0,dimsFor(2400),dimsFor(1800)];
    }
    var ctx=srcCv.getContext('2d');
    var px=ctx.getImageData(0,0,srcCv.width,srcCv.height).data;
    var lastErr=null;
    for(var ti=0;ti<tiers.length;ti++){
      try{
        var wdt=tiers[ti][0], hgt=tiers[ti][1];
        var warped=CV.warp(px,srcCv.width,srcCv.height,q,wdt,hgt);
        var filtered=CV.applyFilter(warped,wdt,hgt,filter);
        var out=document.createElement('canvas'); out.width=wdt; out.height=hgt;
        out.getContext('2d').putImageData(new ImageData(filtered,wdt,hgt),0,0);
        return out;
      }catch(err){ lastErr=err; }
    }
    throw lastErr||new Error('makePage');
  },
  /* picture export: final cropped + filtered page renders (the same output
     path the PDF export uses), one image file per page */
  exportPictures:function(pages,fmt){
    var isPng=(fmt==='png');
    var chain=Promise.resolve(), files=[];
    (pages||[]).forEach(function(p,i){
      chain=chain.then(function(){ return isPng?canvasPng(p.cv):canvasJpg(p.cv,0.92); })
        .then(function(bytes){
          files.push({name:'onaro-scan-p'+(i+1)+(isPng?'.png':'.jpg'),
            bytes:bytes, mime:isPng?'image/png':'image/jpeg'});
        });
    });
    return chain.then(function(){ return files; });
  },
  /* Blank-frame gate for the live viewfinder: a camera that hasn't started
     rendering (black/unplaying video) has ~zero luma variance. Such frames
     must NEVER be reported as "page locked" — they keep the aiming hint. */
  _camBlank:function(dp){
    var n=0,mean=0,m2=0,i,v;
    for(i=0;i<dp.length;i+=16){ v=dp[i]; n++; var d=v-mean; mean+=d/n; m2+=d*d; }
    var vari=n>1?m2/(n-1):0;
    return vari<30;
  },
  /* ============ LIVE CAMERA VIEWFINDER (CamScanner-style) ============
     Full-screen in-app camera: rear stream, real-time edge detection drawn as
     an overlay (~5fps on downscaled frames), big shutter button.
     getUserMedia is called synchronously from the tap handler (iOS gesture
     rule); permission explainer goes through the non-blocking nudge(). */
  camView:function(body){
    /* idempotent entry: kill any orphan session first — two concurrent iPhone
       camera sessions leave the second <video> black */
    if(SCAN._camStop){ try{ SCAN._camStop(); }catch(e){} SCAN._camStop=null; }
    /* came here from "Use this page": remember locally, then clear the global
       so a fresh "Take photo" entry doesn't inherit the fallback */
    var afterApply=!!SCAN._camAfterApply; SCAN._camAfterApply=false;
    body.innerHTML='<div class="sc-camwrap"><video data-vid playsinline muted autoplay></video>'+
      '<canvas data-ov class="sc-camov"></canvas>'+
      '<div class="sc-camhud"><button class="sc-x" data-camx aria-label="'+esc(t('scan.close'))+'">✕</button>'+
      '<div class="sc-camtip" data-camtip>'+esc(t('scan.camHint'))+'</div><div class="sc-xsp"></div></div>'+
      '<div class="sc-scanline"></div>'+
      '<button class="sc-pagespill" data-pagespill hidden aria-label="'+esc(t('scan.pagesTitle'))+'">'+
      '<span class="sc-pillthumb" data-pillthumb></span><span class="sc-pillcount" data-pillcount></span></button>'+
      '<div class="sc-cambar"><button class="sc-shutter" data-cap aria-label="'+esc(t('scan.camCapture'))+'"></button></div></div>';
    var vid=body.querySelector('[data-vid]'), ov=body.querySelector('[data-ov]');
    /* iOS quirk: the muted attribute alone does NOT reliably mute — the
       property must be set or play() can silently fail and the video stays
       black. Same for playsInline. */
    try{ vid.muted=true; vid.playsInline=true; }catch(e){}
    var octx=ov.getContext('2d');
    var stream=null, rafId=0, lastDet=0, alive=true, wdTimer=0, vidReady=false;
    var healthTimer=0, lastCT=0, lastLumaMean=-1, frozenCT=0, acqTries=0;
    /* saved-pages pill: count badge + last-page thumbnail, tappable -> pagesView */
    function paintPill(){
      var pill=body.querySelector('[data-pagespill]'); if(!pill) return;
      var n=SCAN.pages.length;
      pill.hidden=!n;
      if(!n) return;
      body.querySelector('[data-pillcount]').textContent=n;
      var th=body.querySelector('[data-pillthumb]');
      try{
        var tc=SCAN._thumb(SCAN.pages[n-1].cv,72); /* stepped: no moire */
        th.innerHTML=''; var im=new Image(); im.alt=''; im.src=tc.toDataURL('image/jpeg',0.7); th.appendChild(im);
      }catch(e){ th.innerHTML='&#128444;'; }
      pill.classList.remove('sc-pillpop'); void pill.offsetWidth; pill.classList.add('sc-pillpop');
    }
    body.querySelector('[data-pagespill]').onclick=function(){ stopAll(); SCAN._capHook=null; SCAN.pagesView(body); };
    paintPill();
    var dcv=document.createElement('canvas');
    /* the shutter stays visibly disabled until the camera actually delivers
       frames — a premature tap was a silent no-op */
    var capBtn=body.querySelector('[data-cap]');
    if(capBtn) capBtn.disabled=true;
    function markReady(){ vidReady=true; if(capBtn) capBtn.disabled=false; }
    /* paper tracker: smoothed quad in detection-frame coords (+ its frame size),
       or the aim guide when no paper-like quad is locked. */
    var trk={q:null,score:0,lost:0}, trkW=0, trkH=0, trkGuide=true;
    function accent(){ try{ return (getComputedStyle(document.body).getPropertyValue('--accent')||'').trim()||'#b6e332'; }catch(e){ return '#b6e332'; } }
    /* tracked quad (or the A4 aim guide) in video-frame coords */
    function liveQuad(vw,vh){
      if(trk.q&&trkW&&trkH){
        var sx=vw/trkW, sy=vh/trkH;
        return trk.q.map(function(p){ return {x:p.x*sx, y:p.y*sy}; });
      }
      return CV.guideRect(vw,vh);
    }
    function stopAll(){ alive=false; cancelAnimationFrame(rafId); clearTimeout(wdTimer); clearInterval(healthTimer); healthTimer=0;
      if(stream){ try{ stream.getTracks().forEach(function(tr){ tr.stop(); }); }catch(e){} stream=null; }
      if(SCAN._camStop===stopAll) SCAN._camStop=null;
      document.removeEventListener('visibilitychange',onVis); }
    SCAN._camStop=stopAll;
    /* watchdog: if the video never actually starts rendering (black view),
       never leave the user staring at it — show an explicit error card.
       After "Use this page", a dead camera falls back to the saved pages
       instead of stranding the flow. */
    function camFail(diag){
      /* a dead camera abandons any pending capture redirect — otherwise the
         next shutter would fire into this detached session */
      SCAN._capHook=null;
      if(afterApply&&SCAN.pages.length){ stopAll(); SCAN.pagesView(body); return; }
      stopAll();
      body.innerHTML='<div class="sc-col" style="padding:28px 18px;text-align:center;gap:12px">'+
        '<div class="sc-sect">'+esc(t('scan.camFail'))+'</div>'+
        '<div class="sc-note">'+esc(t('scan.camFailHint'))+'</div>'+
        (diag?'<div class="sc-note" style="font-family:monospace;font-size:11px;opacity:.65">diag: '+esc(diag)+'</div>':'')+
        '<button class="sc-btn sc-primary sc-wide" data-retry>'+esc(t('scan.tryAgain'))+'</button>'+
        (SCAN.pages.length?'<button class="sc-btn sc-wide" data-seepages>'+esc(t('scan.viewPages'))+' ('+SCAN.pages.length+')</button>':'')+
        '<button class="sc-btn sc-wide" data-backx>'+esc(t('scan.close'))+'</button></div>';
      body.querySelector('[data-retry]').onclick=function(){ SCAN.camView(body); };
      var spb=body.querySelector('[data-seepages]');
      if(spb) spb.onclick=function(){ SCAN.pagesView(body); };
      body.querySelector('[data-backx]').onclick=function(){ SCAN.start(body,true); };
    }
    function layoutOv(){
      var r=vid.getBoundingClientRect();
      var dpr=Math.min(2,window.devicePixelRatio||1);
      ov.width=Math.max(1,Math.round(r.width*dpr)); ov.height=Math.max(1,Math.round(r.height*dpr));
      octx.setTransform(dpr,0,0,dpr,0,0);
      return r;
    }
    /* video-frame coords -> css px inside the element (object-fit:cover math) */
    function f2v(px,py,r){
      var vw=vid.videoWidth, vh=vid.videoHeight;
      var s=Math.max(r.width/vw,r.height/vh), dw=vw*s, dh=vh*s;
      return [(r.width-dw)/2+px/vw*dw, (r.height-dh)/2+py/vh*dh];
    }
    function drawOv(r){
      var vw=vid.videoWidth, vh=vid.videoHeight;
      if(!vw||!vh) return;
      octx.clearRect(0,0,r.width,r.height);
      var q=liveQuad(vw,vh);
      var pts=q.map(function(p){ return f2v(p.x,p.y,r); });
      var A=accent(), i;
      if(trkGuide){
        /* no paper locked: subtle dashed A4 aim guide, NO dimming — the user
           must see the paper to aim at it. Never a wild quad. */
        octx.save();
        octx.setLineDash([9,7]);
        octx.strokeStyle='rgba(255,255,255,0.65)'; octx.lineWidth=2;
        octx.beginPath();
        octx.moveTo(pts[0][0],pts[0][1]);
        for(i=1;i<4;i++) octx.lineTo(pts[i][0],pts[i][1]);
        octx.closePath(); octx.stroke();
        octx.restore();
        return;
      }
      octx.beginPath();
      octx.rect(0,0,r.width,r.height);
      octx.moveTo(pts[0][0],pts[0][1]);
      for(i=1;i<4;i++) octx.lineTo(pts[i][0],pts[i][1]);
      octx.closePath();
      octx.fillStyle='rgba(0,0,0,0.55)'; octx.fill('evenodd');
      octx.beginPath();
      octx.moveTo(pts[0][0],pts[0][1]);
      for(i=1;i<4;i++) octx.lineTo(pts[i][0],pts[i][1]);
      octx.closePath();
      octx.strokeStyle=A; octx.lineWidth=3; octx.stroke();
      pts.forEach(function(p){
        octx.beginPath(); octx.arc(p[0],p[1],8,0,6.2832);
        octx.fillStyle=A; octx.fill();
        octx.lineWidth=2.5; octx.strokeStyle='#fff'; octx.stroke();
      });
    }
    function loop(){
      if(!alive) return;
      rafId=requestAnimationFrame(loop);
      var vw=vid.videoWidth, vh=vid.videoHeight;
      if(!vw||!vh||document.hidden) return;
      var r=layoutOv(), now=performance.now();
      if(now-lastDet>300){
        lastDet=now;
        try{
          var dw=320, dh=Math.max(1,Math.round(320*vh/vw));
          dcv.width=dw; dcv.height=dh;
          var dctx=dcv.getContext('2d'); dctx.drawImage(vid,0,0,dw,dh);
          var dp=dctx.getImageData(0,0,dw,dh).data;
          /* frame luma snapshot for the stream-health monitor */
          try{ var _lm=0,_ln=0,_li; for(_li=0;_li<dp.length;_li+=64){ _lm+=dp[_li]; _ln++; } lastLumaMean=_ln?_lm/_ln:-1; }catch(e){}
          /* blank/black frames (camera not rendering yet) must never report
             "locked" — keep the aiming hint instead of lying */
          var blank=SCAN._camBlank(dp);
          var res=blank?{guide:true}:CV.detectLive(dp,dw,dh,trk);
          trkW=dw; trkH=dh; trkGuide=res.guide;
          /* honest viewfinder tip: locked -> capture prompt; no lock ->
             say so plainly instead of drawing a bogus box */
          var tipEl=body.querySelector('[data-camtip]');
          if(tipEl){
            var tk=blank?'scan.camHint':(res.guide?'scan.camNoDoc':'scan.camLocked');
            if(tipEl.__tk!==tk){ tipEl.__tk=tk; tipEl.textContent=t(tk); }
          }
        }catch(e){}
      }
      drawOv(r);
    }
    function onVis(){ if(!alive) return;
      if(document.hidden){ cancelAnimationFrame(rafId); }
      else if(stream){ cancelAnimationFrame(rafId); loop(); } }
    document.addEventListener('visibilitychange',onVis);
    function denied(){
      stopAll(); SCAN._capHook=null;
      if(HUB.perms&&HUB.perms.rescue){
        HUB.perms.rescue('camera','denied').then(function(again){
          if(again) SCAN.camView(body); else SCAN.start(body,true);
        });
      }else{ SCAN.start(body,true); }
    }
    body.querySelector('[data-camx]').onclick=function(){ stopAll(); SCAN._capHook=null; if(SCAN.pages.length) SCAN.pagesView(body); else SCAN.start(body,true); };
    body.querySelector('[data-cap]').onclick=function(){
      var vw=vid.videoWidth, vh=vid.videoHeight;
      if(!vw||!vh) return;
      cancelAnimationFrame(rafId); alive=false;
      function finish(fc,isPhoto){
        var q=liveQuad(fc.width,fc.height); /* tracked paper (scaled to the still), or the A4 aim guide */
        if(isPhoto){
          /* The takePhoto still is a LARGER, differently-cropped sensor readout
             than the video frame the live quad was tracked on (and possibly a
             different aspect): mapping the video quad over with independent
             x/y scale stretches it. Re-detect directly in photo space so the
             quad is self-consistent with the pixels being warped. Falls back
             to the video-mapped quad when detection finds nothing.
             IMPORTANT: detectQuad returns a near-full-frame quad (4% inset ≈
             85% of frame area) when it finds nothing. Accept the re-detected
             quad ONLY if it covers <82% of the photo — otherwise the user gets
             an uncropped full photo instead of the paper they saw locked on
             screen. */
          try{
            var pq=SCAN.detectQuad(fc);
            if(pq&&pq.length===4){
              var pArea=0;
              try{ pArea=CV.quadArea(pq); }catch(e2){ pArea=0; }
              if(pArea>0&&pArea<fc.width*fc.height*0.82) q=pq;
            }
          }catch(e){}
        }
        /* capture-time refinement: re-snap the live-tracked quad on the
           full-res still (edge-snapped + re-intersected corners) so the warp
           comes out level like CamScanner. Falls back to the live quad. */
        if(!trkGuide||isPhoto){
          try{
            var fpx=fc.getContext('2d').getImageData(0,0,fc.width,fc.height).data;
            var rq=CV.refineCapture(fpx,fc.width,fc.height,q);
            if(rq&&rq.length===4) q=rq;
          }catch(e){}
        }
        stopAll();
        var hook=SCAN._capHook; SCAN._capHook=null;
        if(hook){ hook(fc,q); } else SCAN.cropView(body,fc,q,'cam');
      }
      function frameGrab(){
        var fc=document.createElement('canvas'); fc.width=vw; fc.height=vh;
        try{ fc.getContext('2d').drawImage(vid,0,0,vw,vh); }
        catch(e){ stopAll(); SCAN.start(body,true); return; }
        finish(fc);
      }
      /* Full-resolution still when the platform offers it (ImageCapture),
         otherwise the native video frame. Either way: native sensor pixels,
         never an upscaled preview. */
      var vtrack=(stream&&stream.getVideoTracks&&stream.getVideoTracks()[0])||null;
      if(vtrack&&window.ImageCapture){
        try{
          var ic=new ImageCapture(vtrack);
          R.busy(body,true);
          ic.takePhoto().then(function(blob){
            R.busy(body,false);
            if(window.createImageBitmap){
              /* EXIF orientation: iPhone takePhoto blobs are sensor-landscape
                 with an EXIF rotation flag. Without imageOrientation:'from-image'
                 the canvas gets an UNROTATED landscape image while the live
                 video quad is portrait -> the quad maps into the wrong space
                 and the warp comes out distorted. */
              try{ return createImageBitmap(blob,{imageOrientation:'from-image'}); }catch(e){}
              return createImageBitmap(blob);
            }
            return new Promise(function(res,rej){
              var url=URL.createObjectURL(blob), im=new Image();
              im.onload=function(){ URL.revokeObjectURL(url); res(im); };
              im.onerror=function(e){ URL.revokeObjectURL(url); rej(e); };
              im.src=url;
            });
          }).then(function(bm){
            var bw=bm.width||bm.naturalWidth||vw, bh=bm.height||bm.naturalHeight||vh;
            var fc=document.createElement('canvas'); fc.width=bw; fc.height=bh;
            try{ fc.getContext('2d').drawImage(bm,0,0,bw,bh); }
            catch(e){ frameGrab(); return; }
            if(bm.close){ try{bm.close();}catch(e2){} }
            finish(fc,true); /* full-res photo: re-detect in photo space */
          }).catch(function(){ R.busy(body,false); frameGrab(); });
          return;
        }catch(e){ /* fall through to frameGrab */ }
      }
      frameGrab();
    };
    if(HUB.perms) HUB.perms.nudge('camera'); /* non-blocking; already called by gateTake, suppressed as duplicate */
    /* ---- stream startup: 1080p cap (thermal/decoder headroom on iPhone —
       the still path grabs full sensor res independently), a repair ladder
       (re-play, then one fresh getUserMedia), and a 2s stream-health monitor
       that reports a diagnostic code instead of guessing. ---- */
    SCAN._camDiag='init'; SCAN._camHealthLog=[];
    function diagCode(){
      var trk=(stream&&stream.getVideoTracks&&stream.getVideoTracks()[0])||null;
      var ts=trk?(trk.readyState==='live'?1:(trk.readyState==='ended'?0:-1)):-2;
      var tm=trk?(trk.muted?1:0):-1;
      var lm=lastLumaMean<0?-1:(lastLumaMean<15?0:(lastLumaMean>100?2:1));
      return 'v'+vid.readyState+'p'+(vid.paused?1:0)+'m'+(vid.muted?1:0)+
        'c'+(vid.currentTime>lastCT?1:0)+' t'+ts+'mu'+tm+' f'+lm;
    }
    function noteHealth(){
      var code=diagCode();
      SCAN._camDiag=code;
      SCAN._camHealthLog.push({t:Date.now(),code:code});
      if(SCAN._camHealthLog.length>12) SCAN._camHealthLog.shift();
      return code;
    }
    function killStream(){
      if(stream){ try{ stream.getTracks().forEach(function(tr){ tr.stop(); }); }catch(e){} stream=null; }
    }
    function sampleHealth(){
      if(!alive||!stream||document.hidden) return;
      var code=noteHealth();
      var trk=(stream.getVideoTracks&&stream.getVideoTracks()[0])||null;
      var deadTrack=!!(trk&&trk.readyState==='ended');
      if(vid.currentTime<=lastCT) frozenCT++; else frozenCT=0;
      lastCT=vid.currentTime;
      /* dead track, or a decoder that froze after previously delivering
         frames: repair once, then the honest error card with the code */
      if(deadTrack||(vidReady&&vid.readyState>=2&&frozenCT>=2)){
        if(acqTries<2){ killStream(); vidReady=false; frozenCT=0; if(capBtn) capBtn.disabled=true; acquire(); }
        else camFail(code);
      }
    }
    function acquire(){
      if(!alive) return;
      acqTries++;
      var failed=false;
      function noFrame(){
        if(!alive||failed) return;
        if(vidReady&&vid.videoWidth) return; /* healthy */
        if(acqTries<2){
          /* ladder step 1: nudge play() again (iOS gesture-chain quirk) */
          try{ var pr=vid.play(); if(pr&&pr.catch) pr.catch(function(){}); }catch(e){}
          wdTimer=setTimeout(function(){
            if(!alive||failed) return;
            if(vidReady&&vid.videoWidth) return;
            killStream(); acquire(); /* ladder step 2: fresh getUserMedia, once */
          },3000);
        }else{
          camFail(noteHealth()); /* ladder exhausted: honest card + diag code */
        }
      }
      try{
        Promise.resolve(navigator.mediaDevices.getUserMedia(
          {video:{facingMode:{ideal:'environment'},width:{ideal:1920},height:{ideal:1080}},audio:false})
        ).then(function(s){
          if(!alive||failed){ try{ s.getTracks().forEach(function(tr){ tr.stop(); }); }catch(e){} return; }
          cancelAnimationFrame(rafId); /* never run two rAF chains */
          stream=s; vid.srcObject=s;
          vid.addEventListener('playing',markReady,{once:true});
          wdTimer=setTimeout(noFrame,3500);
          try{ var pr2=vid.play(); if(pr2&&pr2.catch) pr2.catch(function(){}); }catch(e){}
          loop();
          if(!healthTimer) healthTimer=setInterval(sampleHealth,2000);
        },function(){ failed=true; denied(); });
      }catch(e){ failed=true; denied(); }
    }
    acquire();
  },
  /* ============ CROP / ADJUST SCREEN (CamScanner-style) ============
     Dimmed mask OUTSIDE the document (never a tint over it), bright volt
     border, four 48px draggable corner handles. A live output preview
     re-renders instantly per filter tap: the warp is computed once per
     quad/size and all four filtered variants are cached, so switching
     filters is a single putImageData — no lag, no spinner. */
  cropView:function(body,srcCv,preQ,from,session,idx){
    /* Review session: every capture in this visit. Each item keeps its own
       source canvas, quad, filter, size, warp cache, and confirmed-page ref.
       CamScanner pattern (original Onaro styling): the hero is the CROPPED
       paper with the selected filter; the raw photo + draggable quad lives
       behind the Crop toggle; a 1/n pager with prev/next + trash sits on the
       preview; bottom row = Retake | Rotate | Crop | ✓ Use this page.
       Default view on entry is the cropped preview. */
    function mkItem(cv,qq){ return SCAN._mkItem(cv,qq); }
    var sess=(session&&session.length)?session:[mkItem(srcCv,preQ)];
    var si=(idx==null?sess.length-1:idx); if(si<0)si=0; if(si>=sess.length)si=sess.length-1;
    function it(){ return sess[si]; }
    var view='preview';
    var FILTERS=[['color','scan.filterColor'],['magic','scan.filterMagic'],['gray','scan.filterGray'],['bw','scan.filterBw']];
    var SIZES=[['auto','scan.sizeAuto'],['a4','scan.sizeA4'],['letter','scan.sizeLetter'],['legal','scan.sizeLegal']];
    body.innerHTML=
      '<div class="sc-prevbar">'+
        '<button class="sc-icbtn" data-del aria-label="'+esc(t('scan.delPage'))+'">🗑</button>'+
        '<div class="sc-pageind"><button class="sc-pgbtn" data-pgprev aria-label="‹">‹</button>'+
        '<span data-pgnum></span><button class="sc-pgbtn" data-pgnext aria-label="›">›</button></div>'+
        '<span class="sc-xsp"></span>'+
      '</div>'+
      '<div class="sc-prevwrap" data-prevw><canvas data-prev></canvas></div>'+
      '<div class="sc-note" data-adjnote hidden>'+esc(t('scan.adjustHint'))+'</div>'+
      '<div class="sc-adjust" data-adj hidden><canvas data-photo></canvas>'+
      '<svg data-mask preserveAspectRatio="none"></svg>'+
      '<svg data-border preserveAspectRatio="none"></svg>'+
      '<div class="sc-chandle" data-h="0" role="slider" aria-label="'+esc(t('scan.adjustHint'))+'"></div>'+
      '<div class="sc-chandle" data-h="1" role="slider" aria-label="'+esc(t('scan.adjustHint'))+'"></div>'+
      '<div class="sc-chandle" data-h="2" role="slider" aria-label="'+esc(t('scan.adjustHint'))+'"></div>'+
      '<div class="sc-chandle" data-h="3" role="slider" aria-label="'+esc(t('scan.adjustHint'))+'"></div></div>'+
      '<div class="sc-secttl">'+esc(t('scan.filters'))+'</div>'+
      '<div class="sc-fthumbs" data-thumbs>'+
      FILTERS.map(function(f){ return '<button class="sc-fthumb" data-f="'+f[0]+'">'+
        '<canvas data-tc="'+f[0]+'"></canvas><span>'+esc(t(f[1]))+'</span></button>'; }).join('')+'</div>'+
      '<div class="sc-secttl">'+esc(t('scan.pageSize'))+'</div>'+
      '<div class="sc-sizebar" data-sb>'+
      SIZES.map(function(s){ return '<button class="sc-fbtn" data-s="'+s[0]+'">'+esc(t(s[1]))+'</button>'; }).join('')+'</div>'+
      '<div class="sc-sizedims" data-dims></div>'+
      '<div class="sc-row"><button class="sc-btn sc-btn-ghost" data-back></button>'+
      '<button class="sc-btn sc-btn-ghost" data-rot>\u27F3 '+esc(t('scan.rotate'))+'</button>'+
      '<button class="sc-btn sc-btn-ghost" data-cropbtn></button>'+
      '<button class="sc-btn sc-primary" data-apply>\u2713 '+esc(t('scan.usePage'))+'</button></div>';
    var adj=body.querySelector('[data-adj]'),
        adjNote=body.querySelector('[data-adjnote]'),
        prevWrap=body.querySelector('[data-prevw]'),
        photo=body.querySelector('[data-photo]'),
        mask=body.querySelector('[data-mask]'),
        border=body.querySelector('[data-border]'),
        handles=Array.prototype.slice.call(body.querySelectorAll('[data-h]')),
        pv=body.querySelector('[data-prev]'),
        dimsEl=body.querySelector('[data-dims]'),
        pgnum=body.querySelector('[data-pgnum]'),
        pgprev=body.querySelector('[data-pgprev]'),
        pgnext=body.querySelector('[data-pgnext]'),
        cropBtn=body.querySelector('[data-cropbtn]'),
        backBtn=body.querySelector('[data-back]');
    /* an edit after confirm drops the item back to unconfirmed, so the saved
       set never holds a stale render */
    function unconfirm(cur){
      if(cur.pgRef>=0&&cur.pgRef<SCAN.pages.length){
        SCAN.pages.splice(cur.pgRef,1);
        sess.forEach(function(o){ if(o.pgRef>cur.pgRef)o.pgRef--; });
        cur.pgRef=-1;
      }
    }
    function paintIndicator(){
      pgnum.textContent=(si+1)+'/'+sess.length;
      pgprev.disabled=si<=0; pgnext.disabled=si>=sess.length-1;
    }
    function paintSel(){
      var cur=it();
      body.querySelectorAll('[data-f]').forEach(function(b){
        b.classList.toggle('on',b.getAttribute('data-f')===cur.filter); });
      body.querySelectorAll('[data-s]').forEach(function(b){
        b.classList.toggle('on',b.getAttribute('data-s')===cur.size); });
    }
    function paintCropBtn(){
      cropBtn.innerHTML=(view==='preview'?'\u26F6 ':'\u2713 ')+esc(t(view==='preview'?'scan.adjustCorners':'scan.doneAdjust'));
    }
    function setView(v){
      view=v;
      var adjMode=(v==='adjust');
      adj.hidden=!adjMode; adjNote.hidden=!adjMode; prevWrap.hidden=adjMode;
      paintCropBtn();
      if(adjMode){ paintOverlay(); } else { renderPreview(); }
    }
    var thumbTmp=document.createElement('canvas'), tcMap={};
    body.querySelectorAll('[data-thumbs] [data-tc]').forEach(function(c){
      tcMap[c.getAttribute('data-tc')]=c;
    });
    function paintThumbs(){
      var cache=it().cache;
      FILTERS.forEach(function(f){
        var c=tcMap[f[0]]; if(!c||!cache.imgs) return;
        var tw=104, th=Math.max(64,Math.round(tw*cache.h/cache.w));
        c.width=tw; c.height=th;
        thumbTmp.width=cache.w; thumbTmp.height=cache.h;
        thumbTmp.getContext('2d').putImageData(new ImageData(cache.imgs[f[0]],cache.w,cache.h),0,0);
        c.getContext('2d').drawImage(thumbTmp,0,0,tw,th);
      });
    }
    function paintOverlay(){
      var cur=it(), W=cur.W, H=cur.H, q=cur.q;
      var d='M0 0H'+W+'V'+H+'H0Z M'+q[0].x+' '+q[0].y+'L'+q[1].x+' '+q[1].y+
            'L'+q[2].x+' '+q[2].y+'L'+q[3].x+' '+q[3].y+'Z';
      mask.innerHTML='<path d="'+d+'" fill-rule="evenodd" class="sc-maskpath"/>';
      border.innerHTML='<polygon points="'+q.map(function(p){ return p.x+','+p.y; }).join(' ')+'" class="sc-borderpoly"/>';
      handles.forEach(function(h,i){
        h.style.left=(q[i].x/W*100)+'%'; h.style.top=(q[i].y/H*100)+'%';
      });
    }
    function warpKey(){
      var cur=it();
      return cur.q.map(function(p){ return Math.round(p.x)+'x'+Math.round(p.y); }).join(',')+'|'+cur.size;
    }
    function fullDims(){
      var cur=it(), d=SCAN.pageDims(cur.q,cur.size);
      return d[0]+' × '+d[1]+' px';
    }
    /* big preview: the warped crop fills the frame edge-to-edge (quad corners
       map exactly to canvas corners — zero background margins by construction) */
    function renderPreview(){
      var cur=it(), k=warpKey();
      if(k!==cur.cache.key){
        var asp=SCAN.pageAspect(cur.q,cur.size), pw=480, ph=Math.round(pw/asp);
        if(ph>700){ ph=700; pw=Math.max(200,Math.round(ph*asp)); }
        var warped=CV.warp(cur.srcPx,cur.W,cur.H,cur.q,pw,ph);
        cur.cache={key:k,w:pw,h:ph,imgs:{
          color:warped,
          gray:CV.applyFilter(warped,pw,ph,'gray'),
          bw:CV.applyFilter(warped,pw,ph,'bw'),
          magic:CV.applyFilter(warped,pw,ph,'magic')
        }};
        paintThumbs(); /* quad/size changed -> refresh thumbnails too */
      }
      var cache=cur.cache;
      pv.width=cache.w; pv.height=cache.h;
      pv.getContext('2d').putImageData(new ImageData(cache.imgs[cur.filter],cache.w,cache.h),0,0);
      dimsEl.textContent=fullDims();
    }
    function paintItem(){
      var cur=it();
      photo.width=cur.W; photo.height=cur.H;
      photo.getContext('2d').drawImage(cur.cv,0,0);
      mask.setAttribute('viewBox','0 0 '+cur.W+' '+cur.H);
      border.setAttribute('viewBox','0 0 '+cur.W+' '+cur.H);
      paintSel(); paintIndicator(); setView('preview');
    }
    var pvT=0;
    function schedulePreview(){ clearTimeout(pvT); pvT=setTimeout(renderPreview,140); }
    handles.forEach(function(h){
      h.addEventListener('pointerdown',function(e){
        e.preventDefault();
        e.stopPropagation();
        /* Pointer capture: retargets all subsequent pointermove/up to this
           handle, so the browser never starts a scroll/zoom gesture even when
           the finger slides off the 48px dot. This is the iOS Safari fix for
           "whole screen moves when dragging a corner". */
        try{ if(h.setPointerCapture) h.setPointerCapture(e.pointerId); }catch(e2){}
        var cur=it(), W=cur.W, H=cur.H, hidx=parseInt(h.getAttribute('data-h'),10);
        unconfirm(cur);
        /* magnifier loupe: a zoomed view around the active corner follows the
           finger so each corner lands pixel-exact (CamScanner pattern). The
           source is the full-res photo, not the downscaled preview. */
        var loupe=document.createElement('div');
        loupe.className='sc-loupe';
        loupe.innerHTML='<canvas width="170" height="170"></canvas>';
        document.body.appendChild(loupe);
        var lctx=loupe.firstChild.getContext('2d');
        function paintLoupe(fx,fy){
          var c=cur.q[hidx], S=84, half=S/2;
          var sx=Math.max(0,Math.min(W-S,c.x-half)), sy=Math.max(0,Math.min(H-S,c.y-half));
          try{
            lctx.fillStyle='#000'; lctx.fillRect(0,0,170,170);
            lctx.drawImage(cur.cv,sx,sy,S,S,0,0,170,170);
            var lx=(c.x-sx)/S*170, ly=(c.y-sy)/S*170;
            lctx.strokeStyle='rgba(255,255,255,.95)'; lctx.lineWidth=2;
            lctx.beginPath();
            lctx.moveTo(lx-16,ly); lctx.lineTo(lx+16,ly);
            lctx.moveTo(lx,ly-16); lctx.lineTo(lx,ly+16);
            lctx.stroke();
            lctx.fillStyle='#fff';
            lctx.beginPath(); lctx.arc(lx,ly,4.5,0,6.2832); lctx.fill();
            lctx.strokeStyle='#111'; lctx.lineWidth=1.5;
            lctx.beginPath(); lctx.arc(lx,ly,4.5,0,6.2832); lctx.stroke();
          }catch(e2){}
          var DS=182, vx=(fx==null?window.innerWidth/2:fx), vy=(fy==null?window.innerHeight/3:fy);
          var px2=Math.max(6,Math.min(window.innerWidth-DS-6,vx-DS/2));
          var py2=vy-DS-24;
          if(py2<6) py2=vy+44;
          loupe.style.left=px2+'px'; loupe.style.top=py2+'px';
        }
        paintLoupe(e.clientX,e.clientY);
        function mv(ev){
          if(ev.cancelable) ev.preventDefault();
          var r=adj.getBoundingClientRect();
          var x=(ev.clientX-r.left)/r.width*W, y=(ev.clientY-r.top)/r.height*H;
          cur.q[hidx]={x:Math.max(0,Math.min(W,x)),y:Math.max(0,Math.min(H,y))};
          paintOverlay(); schedulePreview(); paintLoupe(ev.clientX,ev.clientY);
        }
        function up(){
          try{ if(h.releasePointerCapture) h.releasePointerCapture(e.pointerId); }catch(e2){}
          window.removeEventListener('pointermove',mv);
          window.removeEventListener('pointerup',up);
          window.removeEventListener('pointercancel',up);
          h.removeEventListener('pointermove',mv);
          h.removeEventListener('pointerup',up);
          h.removeEventListener('pointercancel',up);
          if(loupe.parentNode) loupe.parentNode.removeChild(loupe);
          renderPreview();
        }
        window.addEventListener('pointermove',mv,{passive:false});
        window.addEventListener('pointerup',up);
        window.addEventListener('pointercancel',up);
        /* With pointer capture, move/up retarget to the handle itself — listen
           there too so the drag survives even if window listeners miss. */
        h.addEventListener('pointermove',mv,{passive:false});
        h.addEventListener('pointerup',up);
        h.addEventListener('pointercancel',up);
      });
    });
    body.querySelectorAll('[data-f]').forEach(function(b){
      b.onclick=function(){
        var cur=it(); unconfirm(cur); cur.filter=b.getAttribute('data-f');
        paintSel(); renderPreview(); /* cache hit -> instant, no spinner */
      };
    });
    body.querySelectorAll('[data-s]').forEach(function(b){
      b.onclick=function(){
        var cur=it(); unconfirm(cur); cur.size=b.getAttribute('data-s');
        paintSel(); renderPreview();
      };
    });
    pgprev.onclick=function(){ if(si>0){ si--; paintItem(); } };
    pgnext.onclick=function(){ if(si<sess.length-1){ si++; paintItem(); } };
    cropBtn.onclick=function(){ setView(view==='preview'?'adjust':'preview'); };
    function backOut(){
      if(fromCam){ SCAN.camView(body); return; }
      if(SCAN.pages.length) SCAN.pagesView(body); else SCAN.start(body,true);
    }
    body.querySelector('[data-del]').onclick=function(){
      var cur=it(); unconfirm(cur);
      sess.splice(si,1);
      if(!sess.length){ backOut(); return; }
      if(si>=sess.length)si=sess.length-1;
      paintItem();
    };
    /* rotate the current page 90° CW: image, quad, and all derived state */
    body.querySelector('[data-rot]').onclick=function(){
      var cur=it(), W=cur.W, H=cur.H;
      unconfirm(cur);
      var nc=document.createElement('canvas'); nc.width=H; nc.height=W;
      var cx2=nc.getContext('2d');
      cx2.save(); cx2.translate(nc.width/2,nc.height/2); cx2.rotate(Math.PI/2);
      cx2.drawImage(cur.cv,-W/2,-H/2); cx2.restore();
      cur.W=nc.width; cur.H=nc.height;
      var q=cur.q.map(function(p){ return {x:cur.W-p.y, y:p.x}; });
      /* the 90° turn cyclically shifts corner order; restore [TL,TR,BR,BL]
         (top-left-most first) so warp/pageAspect/handles stay consistent and
         the page visibly turns instead of un-turning itself in the output */
      var bi=0, bv=1e18, i;
      for(i=0;i<4;i++){ var vv=q[i].x+q[i].y; if(vv<bv){ bv=vv; bi=i; } }
      cur.q=q.slice(bi).concat(q.slice(0,bi));
      cur.cv=nc;
      cur.srcPx=nc.getContext('2d').getImageData(0,0,cur.W,cur.H).data;
      cur.cache.key=null;
      paintItem();
    };
    var fromCam=(from==='cam');
    backBtn.innerHTML=(fromCam?'\uD83D\uDCF7 ':'')+esc(t(fromCam?'scan.retakeCam':'scan.retake'));
    /* Retake replaces the current capture in place (keeps its filter/size);
       the plain Back path leaves the review session. */
    backBtn.onclick=function(){
      if(fromCam){
        var kf=it().filter, ks=it().size;
        SCAN._capHook=function(fc,qq){
          unconfirm(it());
          var ni=mkItem(fc,qq); ni.filter=kf; ni.size=ks;
          sess[si]=ni; paintItem();
        };
        SCAN.camView(body); return;
      }
      backOut();
    };
    var applied=false;
    body.querySelector('[data-apply]').onclick=function(){
      if(applied) return; applied=true; /* rapid-tap guard */
      var cur=it(), out;
      try{ out=SCAN.makePage(cur.cv,cur.q,cur.filter,cur.size); }
      catch(e){ applied=false; R.err(body); return; }
      /* the selected filter is baked into the saved page render, exactly as previewed */
      if(cur.pgRef>=0&&cur.pgRef<SCAN.pages.length){ SCAN.pages[cur.pgRef]={cv:out,filter:cur.filter}; }
      else { SCAN.pages.push({cv:out,filter:cur.filter}); cur.pgRef=SCAN.pages.length-1; }
      applied=false;
      if(ui.toast) try{ ui.toast(t('scan.pageAdded')); }catch(e2){}
      if(fromCam){
        /* continuous scanning: next capture appends to this review session.
           Flag the apply-flow so a dead camera falls back to the saved
           pages instead of stranding the user on a black viewfinder. */
        SCAN._capHook=function(fc,qq){ sess.push(mkItem(fc,qq)); SCAN.cropView(body,fc,qq,from,sess,sess.length-1); };
        SCAN._camAfterApply=true;
        SCAN.camView(body);
      }else SCAN.pagesView(body);
    };
    paintItem();
  },

  pagesView:function(body){
    body.innerHTML='<div class="sc-sect">'+esc(t('scan.pagesTitle'))+' ('+SCAN.pages.length+')</div>'+
      '<div class="sc-note">'+esc(t('scan.scanDocxNote'))+'</div>'+
      '<div class="sc-grid" data-g></div>'+
      '<div class="sc-col" data-exprow><button class="sc-btn sc-wide" data-add>＋ '+esc(t('scan.addPage'))+'</button>'+
      '<button class="sc-btn sc-wide sc-primary" data-exp>'+esc(t('scan.exportPdf'))+'</button>'+
      '<button class="sc-btn sc-wide" data-expw>'+esc(t('scan.exportWord'))+'</button>'+
      '<button class="sc-btn sc-wide" data-expp>🖼️ '+esc(t('scan.exportPic'))+'</button></div>';
    var g=body.querySelector('[data-g]');
    function paint(){
      g.innerHTML='';
      SCAN.pages.forEach(function(p,idx){
        var d=document.createElement('div'); d.className='sc-rpage';
        var th=document.createElement('canvas');
        var tc=SCAN._thumb(p.cv,160); /* stepped downscale: no moire on dense pages */
        th.width=tc.width; th.height=tc.height;
        th.getContext('2d').drawImage(tc,0,0);
        th.style.width='100%'; th.style.height='auto'; th.style.display='block';
        th.style.borderRadius='8px';
        d.appendChild(th);
        d.appendChild(el('<div class="sc-pgnum">'+esc(t('scan.page'))+' '+(idx+1)+'</div>'));
        d.onclick=function(){ SCAN.previewPage(body,idx); };
        var ctl=el('<div class="sc-pgctl"><button data-m="-1">‹</button><button data-x>✕</button><button data-m="1">›</button></div>');
        ctl.querySelector('[data-m="-1"]').onclick=function(e){ e.stopPropagation(); if(idx>0){ var a=SCAN.pages.splice(idx,1)[0]; SCAN.pages.splice(idx-1,0,a); paint(); } };
        ctl.querySelector('[data-m="1"]').onclick=function(e){ e.stopPropagation(); if(idx<SCAN.pages.length-1){ var a2=SCAN.pages.splice(idx,1)[0]; SCAN.pages.splice(idx+1,0,a2); paint(); } };
        ctl.querySelector('[data-x]').onclick=function(e){ e.stopPropagation(); SCAN.pages.splice(idx,1); if(!SCAN.pages.length){ SCAN.start(body,true); return; } SCAN.pagesView(body); };
        d.appendChild(ctl);
        g.appendChild(d);
      });
    }
    paint();
    body.querySelector('[data-add]').onclick=function(){ SCAN.start(body,true); };
    var exporting=false;
    function exportDone(ok){ exporting=false; R.busy(body,false); if(!ok) R.err(body); }
    body.querySelector('[data-exp]').onclick=function(){
      if(exporting||!SCAN.pages.length) return; exporting=true; R.busy(body,true);
      var chain=Promise.resolve(), imgs=[];
      SCAN.pages.forEach(function(p){
        chain=chain.then(function(){ return canvasJpg(p.cv,0.92); }).then(function(b){
          imgs.push({bytes:b,png:false});
        });
      });
      chain.then(function(){ return ENG.imagesToPdf(imgs); }).then(function(pdf){
        return R.saveFiles([{name:'scan.pdf',bytes:pdf,mime:'application/pdf'}]).then(function(){
          body.innerHTML='';
          R.done(body,scIcon('scan-doc'),t('scan.exported'),pdf,R.nm('scan','_'+Date.now()+'.pdf'),'application/pdf');
        });
      }).then(function(){ exportDone(true); },function(){ exportDone(false); });
    };
    body.querySelector('[data-expw]').onclick=function(){
      if(exporting||!SCAN.pages.length) return; exporting=true; R.busy(body,true);
      ENG.scanToDocx(SCAN.pages).then(function(blob){
        var fn=R.nm('scan','_'+Date.now()+'.docx');
        return new Promise(function(res,rej){
          var fr=new FileReader();
          fr.onload=function(){ res(new Uint8Array(fr.result)); };
          fr.onerror=function(){ rej(fr.error); };
          fr.readAsArrayBuffer(blob);
        }).then(function(bytes){
          return DB.add({name:fn,mime:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',bytes:bytes,ts:Date.now()});
        }).then(function(){
          body.innerHTML='';
          R.done(body,scIcon('scan-doc'),t('scan.exportWord'),blob,fn,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
          refreshCount();
        });
      }).then(function(){ exportDone(true); },function(){ exportDone(false); });
    };
    /* picture export: JPG/PNG choice, then one image file per page */
    body.querySelector('[data-expp]').onclick=function(){
      if(exporting||!SCAN.pages.length) return;
      var row=body.querySelector('[data-exprow]');
      row.innerHTML='<div class="sc-note">'+esc(t('scan.exportPic'))+'</div>'+
        '<button class="sc-btn sc-wide sc-primary" data-pf="jpg">'+esc(t('scan.picJpg'))+'</button>'+
        '<button class="sc-btn sc-wide sc-primary" data-pf="png">'+esc(t('scan.picPng'))+'</button>'+
        '<button class="sc-btn sc-wide" data-pfcancel>'+esc(t('scan.cancel'))+'</button>';
      row.querySelector('[data-pfcancel]').onclick=function(){ SCAN.pagesView(body); };
      row.querySelectorAll('[data-pf]').forEach(function(b){
        b.onclick=function(){ doExportPictures(b.getAttribute('data-pf')); };
      });
    };
    function doExportPictures(fmt){
      if(exporting||!SCAN.pages.length) return; exporting=true; R.busy(body,true);
      SCAN.exportPictures(SCAN.pages,fmt).then(function(files){
        return R.saveFiles(files).then(function(){
          body.innerHTML='';
          R.doneMulti(body,scIcon('scan-doc'),t('scan.exportPic'),files);
          refreshCount();
        });
      }).then(function(){ exportDone(true); },function(){ exportDone(false); });
    }
  },
  previewPage:function(body,idx){
    var p=SCAN.pages[idx];
    if(!p){ SCAN.pagesView(body); return; }
    body.innerHTML='<div class="sc-sect">'+esc(t('scan.page'))+' '+(idx+1)+' / '+SCAN.pages.length+'</div>'+
      '<div class="sc-cropwrap"><canvas data-pv style="width:100%;height:auto;display:block"></canvas></div>'+
      '<div class="sc-row"><button class="sc-btn sc-wide" data-pvback>‹ '+esc(t('scan.retake'))+'</button></div>';
    var cv=body.querySelector('[data-pv]');
    var tc2=SCAN._thumb(p.cv,900); /* stepped downscale */
    cv.width=tc2.width; cv.height=tc2.height;
    cv.getContext('2d').drawImage(tc2,0,0);
    body.querySelector('[data-pvback]').onclick=function(){ SCAN.pagesView(body); };
  }
};

/* ================= VIEWS: one per tool ================= */
var VIEWS={
  stub:function(body){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.comingSoon'))+'</div>';
  },
  scan:function(body){ SCAN.start(body); },
  photos2pdf:function(body,file,files){
    R.busy(body,true);
    var chain=Promise.resolve(), imgs=[];
    (files||[file]).forEach(function(f){
      chain=chain.then(function(){
        var b=f.bytes;
        var p=(/heic|heif/i.test(f.mime)||/\.hei[c|f]$/i.test(f.name))?ENG.heicToJpg(b).then(function(jb){ b=jb; }):Promise.resolve();
        return p.then(function(){ return loadImage(b); }).then(function(img){
          var cv=imgToCanvas(img,3000);
          return canvasJpg(cv,0.92).then(function(jb2){ imgs.push({bytes:jb2,png:false}); });
        });
      });
    });
    chain.then(function(){ return ENG.imagesToPdf(imgs); }).then(function(pdf){
      R.busy(body,false);
      R.saveFiles([{name:R.nm(file.name,'.pdf'),bytes:pdf,mime:'application/pdf'}]).then(function(){
        body.innerHTML='';
        R.done(body,scIcon('scan-doc'),t('scan.tPhotos2pdf'),pdf,
          R.nm(file.name,'.pdf'),'application/pdf');
      });
    }).catch(function(){ R.busy(body,false); R.err(body); });
  },
  pdf2word:function(body,file){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.pdf2wordNote'))+'</div>';
    R.busy(body,true);
    ENG.pdfToWord(file.bytes).then(function(blob){
      R.busy(body,false);
      var fn=R.nm(file.name,'.docx');
      new Promise(function(res,rej){
        var fr=new FileReader();
        fr.onload=function(){ res(new Uint8Array(fr.result)); };
        fr.onerror=function(){ rej(fr.error); };
        fr.readAsArrayBuffer(blob);
      }).then(function(bytes){
        return DB.add({name:fn,mime:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',bytes:bytes,ts:Date.now()});
      }).catch(function(){}).then(function(){
        body.innerHTML='<div class="sc-note">'+esc(t('scan.pdf2wordNote'))+'</div>';
        R.done(body,scIcon('scan-doc'),t('scan.tPdf2word'),blob,fn,
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
        refreshCount();
      });
    }).catch(function(err){
      R.busy(body,false);
      if(err&&err.code==='BADTEXT'){ VIEWS.badPdf(body,file); return; }
      R.err(body);
    });
  },
  /* honest dead-end for scrambled/empty PDF text: explain + offer PDF→Images */
  badPdf:function(body,file){
    body.innerHTML='<div class="sc-note sc-err">⚠️ '+esc(t('scan.badPdfTitle'))+'</div>'+
      '<div class="sc-note">'+esc(t('scan.badPdfMsg'))+'</div>'+
      '<button class="sc-btn sc-wide sc-primary" data-alt>'+esc(t('scan.tryPdf2img'))+'</button>';
    body.querySelector('[data-alt]').onclick=function(){ VIEWS.pdf2img(body,file); };
  },
  word2pdf:function(body,file){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.word2pdfNote'))+'</div>';
    R.busy(body,true);
    ENG.wordToHtml(file.bytes).then(function(html){
      R.busy(body,false);
      body.innerHTML='<div class="sc-note">'+esc(t('scan.word2pdfNote'))+'</div>'+
        '<div class="sc-printdoc" data-doc>'+(html||'<p> </p>')+'</div>'+
        '<button class="sc-btn sc-wide sc-primary" data-print>'+esc(t('scan.printSave'))+'</button>';
      body.querySelector('[data-print]').onclick=function(){ window.print(); };
    }).catch(function(){ R.busy(body,false); R.err(body); });
  },
  pdf2img:function(body,file){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.pdf2imgHow'))+'</div>'+
      '<div class="sc-row"><button class="sc-btn" data-s="1">1x</button>'+
      '<button class="sc-btn" data-s="2">2x</button>'+
      '<button class="sc-btn" data-s="3">3x</button></div>';
    body.querySelectorAll('[data-s]').forEach(function(b){
      b.onclick=function(){
        R.busy(body,true);
        ENG.pdfToImages(file.bytes,parseFloat(b.getAttribute('data-s')),'image/png').then(function(imgs){
          R.busy(body,false);
          body.innerHTML='';
          imgs.forEach(function(im,i){
            R.done(body,'🖼️',t('scan.tPdf2img')+' '+(i+1)+'/'+imgs.length,im,
              R.nm(file.name,'_p'+(i+1)+'.png'),'image/png');
          });
          R.saveFiles(imgs.map(function(im,i){
            return {name:R.nm(file.name,'_p'+(i+1)+'.png'),bytes:im,mime:'image/png'};
          }));
        }).catch(function(){ R.busy(body,false); R.err(body); });
      };
    });
  },
  pdf2text:function(body,file){
    R.busy(body,true);
    ENG.pdfText(file.bytes).then(function(texts){
      R.busy(body,false);
      var full=texts.join('\n\n');
      body.innerHTML='<textarea class="sc-textarea" readonly data-ta></textarea>'+
        '<div class="sc-row"><button class="sc-btn" data-copy>'+esc(t('scan.copyText'))+'</button>'+
        '<button class="sc-btn sc-primary" data-share>'+esc(t('scan.share'))+'</button></div>';
      body.querySelector('[data-ta]').value=full;
      body.querySelector('[data-copy]').onclick=function(){
        var ta=body.querySelector('[data-ta]');
        ta.select();
        try{ document.execCommand('copy'); }catch(e){}
        if(navigator.clipboard) navigator.clipboard.writeText(full).catch(function(){});
        if(ui.toast) ui.toast(t('scan.textCopied'));
      };
      body.querySelector('[data-share]').onclick=function(){
        var bytes=new TextEncoder().encode(full);
        R.saveFiles([{name:R.nm(file.name,'.txt'),bytes:bytes,mime:'text/plain'}]).then(function(){
          shareOrDownload(blobOf(bytes,'text/plain'),R.nm(file.name,'.txt'),t('scan.tPdf2text'));
        });
      };
    }).catch(function(){ R.busy(body,false); R.err(body); });
  },
  pdf2excel:function(body,file){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.pdf2excelNote'))+'</div>';
    R.busy(body,true);
    ENG.pdfToExcel(file.bytes).then(function(data){
      R.busy(body,false);
      var bytes=data instanceof Uint8Array?data:new Uint8Array(data);
      var fn=R.nm(file.name,'.xlsx');
      R.saveFiles([{name:fn,bytes:bytes,mime:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}]).then(function(){
        body.innerHTML='<div class="sc-note">'+esc(t('scan.pdf2excelNote'))+'</div>';
        R.done(body,'📊',t('scan.tPdf2excel'),bytes,fn,
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      });
    }).catch(function(){ R.busy(body,false); R.err(body); });
  },
  imgconv:function(body,file){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.imgconvHow'))+'</div>'+
      '<div class="sc-row"><button class="sc-btn" data-m="image/jpeg">JPEG</button>'+
      '<button class="sc-btn" data-m="image/png">PNG</button>'+
      '<button class="sc-btn" data-m="image/webp">WebP</button></div>';
    body.querySelectorAll('[data-m]').forEach(function(b){
      b.onclick=function(){
        var mime=b.getAttribute('data-m');
        R.busy(body,true);
        ENG.convertImage(file.bytes,mime,0.92).then(function(out){
          R.busy(body,false);
          var ext=mime==='image/png'?'.png':(mime==='image/webp'?'.webp':'.jpg');
          var fn=R.nm(file.name,ext);
          R.saveFiles([{name:fn,bytes:out.bytes,mime:mime}]).then(function(){
            body.innerHTML='';
            R.done(body,'🖼️',t('scan.converted'),out.bytes,fn,mime);
          });
        }).catch(function(){ R.busy(body,false); R.err(body); });
      };
    });
  },
  heic2jpg:function(body,file){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.heicNote'))+'</div>';
    R.busy(body,true);
    ENG.heicToJpg(file.bytes).then(function(jpg){
      R.busy(body,false);
      var fn=R.nm(file.name,'.jpg');
      R.saveFiles([{name:fn,bytes:jpg,mime:'image/jpeg'}]).then(function(){
        body.innerHTML='';
        R.done(body,'🖼️',t('scan.converted'),jpg,fn,'image/jpeg');
      });
    }).catch(function(){ R.busy(body,false); R.err(body); });
  },
  merge:function(body,file,files){
    var list=(files&&files.length?files:[file]);
    var names=list.map(function(f){ return esc(f.name); }).join('<br>');
    body.innerHTML='<div class="sc-note">'+esc(t('scan.dMerge'))+'</div>'+
      '<div class="sc-note">'+names+'</div>'+
      '<button class="sc-btn sc-wide sc-primary" data-go>'+esc(t('scan.tMerge'))+'</button>';
    body.querySelector('[data-go]').onclick=function(){
      R.busy(body,true);
      ENG.mergePdfs(list.map(function(f){ return f.bytes; })).then(function(pdf){
        R.busy(body,false);
        var fn=R.nm('merged','_'+Date.now()+'.pdf');
        R.saveFiles([{name:fn,bytes:pdf,mime:'application/pdf'}]).then(function(){
          body.innerHTML='';
          R.done(body,scIcon('scan-doc'),t('scan.merged'),pdf,fn,'application/pdf');
        });
      }).catch(function(){ R.busy(body,false); R.err(body); });
    };
  },
  split:function(body,file){
    body.innerHTML='<div class="sc-note">'+esc(t('scan.splitHow'))+'</div>'+
      '<input class="sc-input" data-ranges placeholder="'+esc(t('scan.splitRangesPh'))+'">'+
      '<button class="sc-btn sc-wide sc-primary" data-go>'+esc(t('scan.tSplit'))+'</button>';
    var base=String(file.name||'file').replace(/\.[^.]+$/,'');
    ENG.loadPdfDoc(file.bytes).then(function(doc){
      var n=doc.numPages;
      body.querySelector('[data-go]').onclick=function(){
        var groups=String(body.querySelector('[data-ranges]').value||'').split(';')
          .map(function(g){ return ENG.parseRanges(g,n); })
          .filter(function(g){ return g.length>0; });
        if(!groups.length){ R.err(body); return; }
        R.busy(body,true);
        ENG.splitPdf(file.bytes,groups).then(function(outs){
          R.busy(body,false);
          body.innerHTML='';
          var chain=Promise.resolve();
          outs.forEach(function(pdf,i){
            chain=chain.then(function(){
              var pages=groups[i];
              var fn=base+'_p'+pages[0]+(pages.length>1?'-p'+pages[pages.length-1]:'')+'.pdf';
              return R.saveFiles([{name:fn,bytes:pdf,mime:'application/pdf'}]).then(function(){
                R.done(body,scIcon('scan-doc'),t('scan.tSplit')+' '+(i+1)+'/'+outs.length,
                  pdf,fn,'application/pdf');
              });
            });
          });
          chain.catch(function(){ R.err(body); });
        }).catch(function(){ R.busy(body,false); R.err(body); });
      };
    }).catch(function(){ R.err(body); });
  }
};

/* ---- rotate / reorder / compress views ---- */
VIEWS.rotate=function(body,file){
  body.innerHTML='<div class="sc-note">'+esc(t('scan.rotateHow'))+'</div>'+
    '<div class="sc-note">'+esc(t('scan.rotateApplies'))+'</div>'+
    '<div class="sc-row"><button class="sc-btn" data-r="90">'+esc(t('scan.rot90'))+'</button>'+
    '<button class="sc-btn" data-r="180">'+esc(t('scan.rot180'))+'</button>'+
    '<button class="sc-btn" data-r="270">'+esc(t('scan.rot270'))+'</button></div>';
  body.querySelectorAll('[data-r]').forEach(function(b){
    b.onclick=function(){
      ENG.rotatePdf(file.bytes,parseInt(b.getAttribute('data-r'),10)).then(function(out){
        R.busy(body,false);
        var fn=R.nm(file.name,'_rotated.pdf');
        R.saveFiles([{name:fn,bytes:out,mime:'application/pdf'}]).then(function(){
          body.innerHTML='';
          R.done(body,scIcon('scan-doc'),t('scan.rotated'),out,fn,'application/pdf');
        });
      }).catch(function(){ R.busy(body,false); R.err(body); });
    };
  });
};
VIEWS.reorder=function(body,file){
  body.innerHTML='<div class="sc-note">'+esc(t('scan.reorderHow'))+'</div><div class="sc-grid" data-g></div>';
  var g=body.querySelector('[data-g]'), order=[];
  ENG.loadPdfDoc(file.bytes).then(function(doc){
    order=[]; for(var i=1;i<=doc.numPages;i++) order.push(i);
    (function paint(){
      g.innerHTML='';
      order.forEach(function(pn,idx){
        var d=document.createElement('div'); d.className='sc-rpage';
        d.innerHTML='<button class="sc-pgx" aria-label="'+esc(t('scan.delete'))+'">✕</button>'+
          '<div class="sc-pgnum">'+pn+'</div>';
        d.querySelector('.sc-pgx').onclick=function(e){
          e.stopPropagation(); order.splice(idx,1); paint();
        };
        var ctl=el('<div class="sc-pgctl"><button data-m="-1">‹</button><button data-m="1">›</button></div>');
        ctl.querySelector('[data-m="-1"]').onclick=function(e){ e.stopPropagation(); if(idx>0){ order.splice(idx,1); order.splice(idx-1,0,pn); paint(); } };
        ctl.querySelector('[data-m="1"]').onclick=function(e){ e.stopPropagation(); if(idx<order.length-1){ order.splice(idx,1); order.splice(idx+1,0,pn); paint(); } };
        d.appendChild(ctl); g.appendChild(d);
      });
    })();
    var b=el('<button class="sc-btn sc-wide sc-primary">'+esc(t('scan.applyOrder'))+'</button>');
    body.appendChild(b);
    b.onclick=function(){
      if(!order.length){ R.err(body); return; }
      R.busy(body,true);
      ENG.reorderPdf(file.bytes,order).then(function(out){
        R.busy(body,false);
        var fn=R.nm(file.name,'_reordered.pdf');
        R.saveFiles([{name:fn,bytes:out,mime:'application/pdf'}]).then(function(){
          body.innerHTML='';
          R.done(body,scIcon('scan-doc'),t('scan.reordered'),out,fn,'application/pdf');
        });
      }).catch(function(){ R.busy(body,false); R.err(body); });
    };
  }).catch(function(){ R.err(body); });
};
VIEWS.compress=function(body,file){
  body.innerHTML='<div class="sc-note">'+esc(t('scan.compressHow'))+'</div>'+
    '<div class="sc-row" data-q>'+
    '<button class="sc-btn" data-qv="0.75">'+esc(t('scan.qHigh'))+'</button>'+
    '<button class="sc-btn" data-qv="0.5">'+esc(t('scan.qMed'))+'</button>'+
    '<button class="sc-btn" data-qv="0.3">'+esc(t('scan.qLow'))+'</button></div>';
  body.querySelectorAll('[data-qv]').forEach(function(b){
    b.onclick=function(){
      R.busy(body,true);
      ENG.compressPdf(file.bytes,parseFloat(b.getAttribute('data-qv'))).then(function(out){
        R.busy(body,false);
        var fn=R.nm(file.name,'_small.pdf');
        R.saveFiles([{name:fn,bytes:out,mime:'application/pdf'}]).then(function(){
          body.innerHTML='';
          R.done(body,scIcon('scan-doc'),
            t('scan.compressed')+' ('+R.fmtSize(file.bytes.length)+' → '+R.fmtSize(out.length)+')',
            out,fn,'application/pdf');
        });
      }).catch(function(){ R.busy(body,false); R.err(body); });
    };
  });
};

/* ================= public API ================= */
HUB.scan={
  cardHTML:function(){
    return '<section class="card sc-card" data-scan-card>'+
      '<div class="sc-cardhead"><div class="sc-cardicon">'+(scIcon('scan-doc'))+'</div>'+
      '<div><div class="sc-cardtitle">'+esc(t('scan.title'))+'</div>'+
      '<div class="sc-cardsub">'+esc(t('scan.tagline'))+'</div></div>'+
      '<div class="sc-count">'+fileCount+'</div></div>'+
      '<div class="sc-quick">'+
      '<button class="sc-qbtn" data-act="scan">'+(scIcon('scan-doc'))+'<span>'+esc(t('scan.quickScan'))+'</span></button>'+
      '<button class="sc-qbtn" data-act="photos2pdf"><span>🖼️</span><span>'+esc(t('scan.tPhotos2pdf'))+'</span></button>'+
      '<button class="sc-qbtn" data-act="pdf2word"><span>📝</span><span>'+esc(t('scan.tPdf2word'))+'</span></button>'+
      '<button class="sc-qbtn" data-act="merge"><span>📚</span><span>'+esc(t('scan.tMerge'))+'</span></button>'+
      '</div>'+
      '<button class="sc-open" data-act="studio">'+esc(t('scan.openStudio'))+' →</button>'+
      '<div class="sc-offline">📵 '+esc(t('scan.savedLocal'))+'</div></section>';
  },
  bind:function(root){
    var card=root.querySelector('[data-scan-card]'); if(!card) return;
    refreshCount();
    card.querySelectorAll('[data-act]').forEach(function(b){
      b.onclick=function(){
        var a=b.getAttribute('data-act');
        if(a==='studio') HUB.scan.studio();
        else HUB.scan.tool(a);
      };
    });
  },
  studio:function(){ R.home(R.overlay(t('scan.studioTitle'))); },
  tool:function(id){
    var tool=null;
    TOOLS.forEach(function(x){ if(x.id===id) tool=x; });
    if(!tool) return;
    var body=R.overlay(t(tool.title)).querySelector('.sc-body');
    if(tool.pick==='none'){ (VIEWS[id]||VIEWS.stub)(body); return; }
    R.pick(body,tool.pick,tool.accept,tool.multi,function(files){
      if(!files.length) return;
      R.saveFiles(files).then(function(){ (VIEWS[id]||VIEWS.stub)(body,files[0],files); });
    });
  },
  TOOLS:TOOLS,
  /* test hooks for QA */
  _t:{
    textQuality:function(pages){ return textQuality(pages); },
    pdfToWord:function(b){ return ENG.pdfToWord(b); },
    pdfText:function(b){ return ENG.pdfText(b); },
    pdfPageItems:function(b){ return ENG.pdfPageItems(b); },
    analyzePage:function(p){ return ENG.analyzePage(p); },
    mergePdfs:function(a){ return ENG.mergePdfs(a); },
    splitPdf:function(b,r){ return ENG.splitPdf(b,r); },
    rotatePdf:function(b,d){ return ENG.rotatePdf(b,d); },
    reorderPdf:function(b,o){ return ENG.reorderPdf(b,o); },
    compressPdf:function(b,q){ return ENG.compressPdf(b,q); },
    imagesToPdf:function(a){ return ENG.imagesToPdf(a); },
    pdfToImages:function(b,s,m){ return ENG.pdfToImages(b,s,m); },
    wordToHtml:function(b){ return ENG.wordToHtml(b); },
    pdfToExcel:function(b){ return ENG.pdfToExcel(b); },
    convertImage:function(b,m,q){ return ENG.convertImage(b,m,q); },
    heicToJpg:function(b){ return ENG.heicToJpg(b); },
    scanToDocx:function(p){ return ENG.scanToDocx(p); },
    detectQuad:function(px,w,h){ return CV.detectQuad(px,w,h); },
    detectLive:function(px,w,h,st){ return CV.detectLive(px,w,h,st); },
    guideRect:function(w,h){ return CV.guideRect(w,h); },
    dbgLive:function(px,w,h){ return CV._dbgLive(px,w,h); },
    dbgAll:function(px,w,h){ return CV._dbgAll(px,w,h); },
    dbgContours:function(px,w,h){ return CV._dbgContours(px,w,h); },
    scanDetectQuad:function(cv){ return SCAN.detectQuad(cv); },
    refineCapture:function(px,w,h,q){ return CV.refineCapture(px,w,h,q); },
    warpFn:function(px,w,h,q,ow,oh){ return CV.warp(px,w,h,q,ow,oh); },
    scanMakePage:function(cv,q,f,s){ return SCAN.makePage(cv,q,f||'color',s); },
    thumbFn:function(px,w,h,tw){ /* pixel-array version of SCAN._thumb for QA */
      var th=Math.max(1,Math.round(h*tw/w));
      function step(p,W,H,dw,dh){
        var out=new Uint8ClampedArray(dw*dh*4);
        for(var y=0;y<dh;y++)for(var x=0;x<dw;x++){
          var sx=Math.min(W-1.001,x*(W-1)/(dw-1)), sy=Math.min(H-1.001,y*(H-1)/(dh-1));
          var x0=Math.floor(sx),y0=Math.floor(sy),fx=sx-x0,fy=sy-y0;
          var o=(y*dw+x)*4,q00=(y0*W+x0)*4;
          for(var c=0;c<4;c++)out[o+c]=p[q00+c]*(1-fx)*(1-fy)+p[q00+4+c]*fx*(1-fy)+p[q00+W*4+c]*(1-fx)*fy+p[q00+W*4+4+c]*fx*fy;
        }
        return out;
      }
      var cw=w,ch=h,cp=px;
      while(cw>tw*2){ var nw=Math.max(1,Math.round(cw/2)),nh=Math.max(1,Math.round(ch/2));
        cp=step(cp,cw,ch,nw,nh); cw=nw; ch=nh; }
      return {px:step(cp,cw,ch,tw,th),w:tw,h:th};
    },
    scanCamView:function(body){ return SCAN.camView(body); },
    scanPages:function(){ return SCAN.pages; },
    camBlank:function(dp){ return SCAN._camBlank(dp); },
    camStop:function(){ if(SCAN._camStop){ try{ SCAN._camStop(); }catch(e){} } return true; },
    scanCropView:function(body,cv,q,from,ses,ix){ return SCAN.cropView(body,cv,q,from,ses,ix); },
    cropMkSession:function(pairs){ return pairs.map(function(p){ return SCAN._mkItem(p.cv,p.q); }); },
    exportPictures:function(pgs,fmt){ return SCAN.exportPictures(pgs,fmt); },
    scanPagesView:function(body){ return SCAN.pagesView(body); },
    scanPages:function(){ return SCAN.pages; },
    scanSetPages:function(a){ SCAN.pages=a; },
    applyFilter:function(px,w,h,f){ return CV.applyFilter(px,w,h,f); },
    parseRanges:function(s,n){ return ENG.parseRanges(s,n); },
    i18nKeys:function(){
      var d=(HUB.i18n&&HUB.i18n._dict)?HUB.i18n._dict('en'):{};
      return Object.keys(d).filter(function(k){ return k.indexOf('scan.')===0; });
    }
  }
};
window.HUB=HUB;
})();

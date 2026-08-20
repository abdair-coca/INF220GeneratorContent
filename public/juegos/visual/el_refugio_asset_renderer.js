(function(global){
"use strict";

/**
 * El Refugio Lógico — Asset Renderer
 * Renderer genérico para el formato JuegoArtDrawCommands.
 * Sin dependencias externas.
 */
class JuegoArtAssetRenderer {
  constructor(manifest){
    if(!manifest || !manifest.assets) throw new Error("Manifest de assets inválido.");
    this.manifest = manifest;
    this.assets = manifest.assets;
  }

  asset(id){
    const a=this.assets[id];
    if(!a) throw new Error("Asset no encontrado: "+id);
    return a;
  }

  resolveState(asset,state,timeMs){
    const states=asset.states||{};
    const key = state && states[state] ? state : Object.keys(states)[0];
    const def=states[key];
    if(!def) return {draw:[],state:key,frame:0};
    if(def.frames && def.frames.length){
      const fps=def.fps||6;
      const frame=Math.floor((timeMs||0)/1000*fps)%def.frames.length;
      return {draw:def.frames[frame].draw||[],state:key,frame};
    }
    return {draw:def.draw||[],state:key,frame:0};
  }

  drawPrimitive(ctx,p,ox,oy){
    ctx.save();
    ctx.globalAlpha = p.alpha == null ? 1 : p.alpha;
    ctx.fillStyle = p.color || "#fff";
    ctx.strokeStyle = p.color || "#fff";
    if(p.type==="rect"){
      ctx.fillRect(Math.round(ox+p.x),Math.round(oy+p.y),Math.round(p.w),Math.round(p.h));
    } else if(p.type==="ellipse"){
      ctx.beginPath();
      ctx.ellipse(ox+p.x,oy+p.y,p.rx,p.ry,0,0,Math.PI*2);
      ctx.fill();
    } else if(p.type==="polygon"){
      if(p.points && p.points.length){
        ctx.beginPath();
        ctx.moveTo(ox+p.points[0][0],oy+p.points[0][1]);
        for(let i=1;i<p.points.length;i++) ctx.lineTo(ox+p.points[i][0],oy+p.points[i][1]);
        ctx.closePath();
        ctx.fill();
      }
    } else if(p.type==="line"){
      ctx.lineWidth=p.width||1;
      ctx.lineCap="square";
      ctx.beginPath();
      ctx.moveTo(ox+p.x1,oy+p.y1);
      ctx.lineTo(ox+p.x2,oy+p.y2);
      ctx.stroke();
    }
    ctx.restore();
  }

  drawAsset(ctx,id,state,worldX,worldY,camera,timeMs,options){
    const asset=this.asset(id);
    const cam=camera||{x:0,y:0};
    const opt=options||{};
    const topX=worldX-asset.anchor.x-cam.x;
    const topY=worldY-asset.anchor.y-cam.y;
    const resolved=this.resolveState(asset,state,timeMs||performance.now());

    ctx.save();
    ctx.imageSmoothingEnabled=false;
    if(opt.alpha!=null) ctx.globalAlpha*=opt.alpha;
    if(opt.flipX){
      ctx.translate(Math.round(topX+asset.size.w),Math.round(topY));
      ctx.scale(-1,1);
      for(const p of resolved.draw) this.drawPrimitive(ctx,p,0,0);
    } else {
      for(const p of resolved.draw) this.drawPrimitive(ctx,p,topX,topY);
    }
    ctx.restore();
    return {asset,state:resolved.state,frame:resolved.frame,topX,topY};
  }

  worldHitbox(id,worldX,worldY){
    const a=this.asset(id);
    if(!a.hitbox) return null;
    const left=worldX-a.anchor.x+a.hitbox.x;
    const top=worldY-a.anchor.y+a.hitbox.y;
    return {x:left,y:top,w:a.hitbox.w,h:a.hitbox.h};
  }

  depthY(id,worldY){
    const a=this.asset(id);
    return worldY + ((a.depth&&a.depth.offsetY)||0);
  }

  sortInstances(instances){
    return [...instances].sort((a,b)=>{
      const ay=this.depthY(a.asset,a.y);
      const by=this.depthY(b.asset,b.y);
      return ay-by;
    });
  }

  drawInstances(ctx,instances,camera,timeMs){
    for(const it of this.sortInstances(instances)){
      this.drawAsset(ctx,it.asset,it.state,it.x,it.y,camera,timeMs,it.options);
    }
  }

  drawPrefab(ctx,prefabId,originX,originY,camera,timeMs){
    const p=this.manifest.prefabs&&this.manifest.prefabs[prefabId];
    if(!p) throw new Error("Prefab no encontrado: "+prefabId);
    const list=(p.objects||[]).map(o=>({
      asset:o.asset,state:o.state,
      x:originX+o.x,y:originY+o.y,
      options:o.options
    }));
    this.drawInstances(ctx,list,camera,timeMs);
  }
}

global.JuegoArtAssetRenderer=JuegoArtAssetRenderer;
})(window);

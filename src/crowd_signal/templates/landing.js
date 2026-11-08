/* Original research-stack scene. Navigation and content work without WebGL. */
(()=>{
 const host=document.getElementById('landing-scene'),button=document.getElementById('landing-motion'),separate=document.getElementById('separate-layers'),status=document.getElementById('scene-status'),visual=document.querySelector('.hero-visual');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let paused=reduced.matches,expanded=false,visible=true,disposed=false,spread={value:0},spreadAnimation=null,renderer=null,raf=0;
 const setButton=()=>{button.setAttribute('aria-pressed',String(!paused));button.setAttribute('aria-label',paused?'Play animation':'Pause animation');button.innerHTML=paused?'▷ <span>Play</span>':'Ⅱ <span>Pause</span>'};
 setButton();
 let draw=()=>{},resetScene=()=>{};document.getElementById('landing-reset').onclick=()=>{resetScene();if(expanded)separate.click();draw()};
 button.onclick=()=>{paused=!paused;if(paused){spreadAnimation?.stop();spread.value=expanded?1:0;for(const a of document.getAnimations())try{a.finish()}catch(e){}}setButton();draw()};
 separate.onclick=()=>{expanded=!expanded;separate.setAttribute('aria-pressed',String(expanded));separate.innerHTML=expanded?'Bring the layers together <span aria-hidden="true">↙</span>':'Separate the layers <span aria-hidden="true">↗</span>';visual.classList.toggle('layers-separated',expanded);status.textContent=expanded?'Price, crowd and models — three separate pages. Select a layer to explore.':'Pointer or ← → to rotate. Select a layer to open its page.';spreadAnimation?.stop();if(window.Motion&&!reduced.matches&&!paused){spreadAnimation=Motion.animate(spread.value,expanded?1:0,{duration:.95,ease:[.22,1,.36,1],onUpdate:v=>{spread.value=v;draw()}})}else{spread.value=expanded?1:0;draw()}};
 reduced.addEventListener('change',e=>{if(e.matches){paused=true;setButton();spreadAnimation?.stop();spread.value=expanded?1:0;draw()}});
 try{
  if(!window.THREE)throw Error('WebGL library unavailable');
  const T=window.THREE;
  renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.setClearColor(0x08090e,0);renderer.outputColorSpace=T.SRGBColorSpace;
  renderer.domElement.setAttribute('aria-hidden','true');host.appendChild(renderer.domElement);
  const scene=new T.Scene(),camera=new T.PerspectiveCamera(33,1,.1,100);camera.position.set(7.2,6.6,9.8);camera.lookAt(0,.15,0);
  scene.add(new T.AmbientLight(0xb8c7ff,2.3));const key=new T.DirectionalLight(0xe6ecff,4);key.position.set(2,8,5);scene.add(key);const blue=new T.PointLight(0x3c5bff,48,20);blue.position.set(-4,1,3);scene.add(blue);const lime=new T.PointLight(0xd6f769,24,16);lime.position.set(3,4,-1);scene.add(lime);
  const group=new T.Group();group.rotation.y=-.3;scene.add(group);const plates=[];
  const plateShape=new T.Shape();const w=4.15,h=2.7,r=.16;plateShape.moveTo(-w/2+r,-h/2);plateShape.lineTo(w/2-r,-h/2);plateShape.quadraticCurveTo(w/2,-h/2,w/2,-h/2+r);plateShape.lineTo(w/2,h/2-r);plateShape.quadraticCurveTo(w/2,h/2,w/2-r,h/2);plateShape.lineTo(-w/2+r,h/2);plateShape.quadraticCurveTo(-w/2,h/2,-w/2,h/2-r);plateShape.lineTo(-w/2,-h/2+r);plateShape.quadraticCurveTo(-w/2,-h/2,-w/2+r,-h/2);
  const geometry=new T.ExtrudeGeometry(plateShape,{depth:.10,bevelEnabled:true,bevelThickness:.025,bevelSize:.035,bevelSegments:2,steps:1});geometry.rotateX(-Math.PI/2);
  const colors=[0x3047ca,0x1d2b55,0x243148];
  for(let i=0;i<3;i++){const plate=new T.Group();plate.userData.base=(i-1)*.75;plate.position.y=plate.userData.base;group.add(plate);plates.push(plate);
   const material=new T.MeshPhysicalMaterial({color:colors[i],roughness:.35,metalness:.55,clearcoat:1,clearcoatRoughness:.2,transparent:true,opacity:.94});plate.add(new T.Mesh(geometry,material));
   const edges=new T.LineSegments(new T.EdgesGeometry(geometry,30),new T.LineBasicMaterial({color:i===2?0xd6f769:0x7f94f6,transparent:true,opacity:i===2?.65:.36}));plate.add(edges);
   // Abstract diagram marks are architecture, never presented as market data.
   const ink=i===2?0xd6f769:i===1?0x9eb4ff:0x829cff;
   if(i===2){const points=[];for(let j=0;j<40;j++){const x=-1.7+j/39*3.4,z=Math.sin(j*.27)*.22+Math.cos(j*.47)*.14;points.push(new T.Vector3(x,.15,z))}plate.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(points),70,.027,6,false),new T.MeshStandardMaterial({color:ink,emissive:ink,emissiveIntensity:.35,roughness:.3})));for(let k=0;k<6;k++){const v=new T.Mesh(new T.BoxGeometry(.055,.018,1.9),new T.MeshBasicMaterial({color:0x7083a5,transparent:true,opacity:.2}));v.position.set(-1.6+k*.64,.14,0);plate.add(v)}}
   else if(i===1){for(let row=0;row<3;row++){const dot=new T.Mesh(new T.SphereGeometry(.08,12,8),new T.MeshStandardMaterial({color:ink}));dot.position.set(-1.55,.17,-.7+row*.66);plate.add(dot);for(let n=0;n<2;n++){const bar=new T.Mesh(new T.BoxGeometry(n?1.25:2.2,.018,.055),new T.MeshBasicMaterial({color:ink,transparent:true,opacity:n?.25:.6}));bar.position.set(n?-.6:-.12,.15,-.7+row*.66+n*.17);plate.add(bar)}}}
   else{for(let j=0;j<7;j++){const column=new T.Mesh(new T.BoxGeometry(.3,.018,.3+j*.16),new T.MeshStandardMaterial({color:ink,metalness:.3,roughness:.4}));column.position.set(-1.5+j*.5,.15,.25);plate.add(column)}}
  }
  const ring=new T.Mesh(new T.TorusGeometry(3.1,.009,8,100),new T.MeshBasicMaterial({color:0x4c5d80,transparent:true,opacity:.5}));ring.rotation.x=Math.PI/2;ring.position.y=-1.4;scene.add(ring);
  const grid=new T.GridHelper(10,20,0x2a3455,0x161e32);grid.position.y=-1.6;grid.material.transparent=true;grid.material.opacity=.35;scene.add(grid);
  let targetX=0,targetY=0,currentX=0,currentY=0,time=0,last=0;resetScene=()=>{targetX=targetY=currentX=currentY=0};
  const pointer=e=>{if(reduced.matches||paused)return;const rect=visual.getBoundingClientRect();targetX=((e.clientX-rect.left)/rect.width-.5)*.25;targetY=((e.clientY-rect.top)/rect.height-.5)*.14;draw()};
  host.addEventListener('keydown',e=>{if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight')return;e.preventDefault();targetX+=e.key==='ArrowLeft'?-.15:.15;currentX=targetX;draw()});visual.addEventListener('pointermove',pointer);visual.addEventListener('pointerleave',()=>{targetX=targetY=0});
  const render=()=>{group.rotation.y=-.3+currentX;group.rotation.x=currentY;plates.forEach((p,i)=>{p.position.y=p.userData.base+(i-1)*spread.value*.68+Math.sin(time+i*.8)*.035;p.rotation.y=(i-1)*spread.value*.085});renderer.render(scene,camera)};
  draw=()=>{if(disposed||!visible||document.hidden)return;render();if(!raf&&!paused)raf=requestAnimationFrame(loop)};
  function loop(now){raf=0;if(disposed||paused||!visible||document.hidden)return;if(now-last>=1000/30){last=now;time+=.014;currentX+=(targetX-currentX)*.08;currentY+=(targetY-currentY)*.08;render()}raf=requestAnimationFrame(loop)}
  const resize=new ResizeObserver(()=>{const width=host.clientWidth,height=host.clientHeight;if(!width||!height)return;renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();draw()});resize.observe(host);
  const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)draw()},{threshold:.05});observer.observe(host);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)draw()});
  const contextLost=e=>{e.preventDefault();paused=true;setButton();status.textContent='The 3D view is unavailable. All research links still work.'};renderer.domElement.addEventListener('webglcontextlost',contextLost);
  window.addEventListener('pageshow',()=>{visible=true;draw()});window.addEventListener('pagehide',e=>{if(e.persisted){visible=false;cancelAnimationFrame(raf);raf=0;return}disposed=true;cancelAnimationFrame(raf);spreadAnimation?.stop();resize.disconnect();observer.disconnect();scene.traverse(o=>{o.geometry?.dispose();if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose()}});renderer.dispose()});
  status.textContent=reduced.matches?'Motion is paused for your reduced-motion preference. Every layer opens a separate page.':'Pointer or ← → to rotate. Select a layer to open its page.';draw();
 }catch(error){renderer?.dispose();host.innerHTML='<div class="scene-fallback-art" aria-hidden="true"><i></i><i></i><i></i></div>';status.textContent='Static view. Every research link is available below.';paused=true;setButton();button.disabled=true;document.getElementById('landing-reset').disabled=true;button.setAttribute('aria-label','Animation unavailable');}
 if(window.Motion&&!reduced.matches){Motion.animate('.market-tag',{opacity:[0,1],y:[12,0]},{duration:.65});Motion.animate('.title-line',{opacity:[0,1],y:[45,0],rotateX:[12,0]},{duration:.95,delay:Motion.stagger(.13,{startDelay:.1}),ease:[.22,1,.36,1]});Motion.animate('.hero-lead,.hero-description,.hero-actions,.hero-proof,.snapshot-note',{opacity:[0,1],y:[18,0]},{duration:.7,delay:Motion.stagger(.08,{startDelay:.4}),ease:[.22,1,.36,1]});Motion.animate('.hero-visual',{opacity:[0,1],scale:[.94,1]},{duration:1.25,delay:.18,ease:[.22,1,.36,1]});document.querySelectorAll('.path-card').forEach(card=>{Motion.hover(card,()=>{if(paused)return;Motion.animate(card,{y:-6},{duration:.24});return()=>Motion.animate(card,{y:0},{duration:.3})})})}
})();

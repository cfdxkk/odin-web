import * as THREE from 'three'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'

export function createAwakeningEffects(scene: THREE.Scene) {
  const uniforms = { time: { value: 0 }, energy: { value: .5 }, warp: { value: 0 }, spectral: { value: 0 } }
  const eclipseMaterial = new THREE.ShaderMaterial({
    uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader: `
      varying vec2 vUv; uniform float time; uniform float energy; uniform float spectral;
      float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
      float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+1.),f.x),f.y);}
      void main(){
        vec2 p=(vUv-.5)*2.; float r=length(p),a=atan(p.y,p.x);
        float n=noise(vec2(a*7.+time*.055,r*22.-time*.09));
        float flame=noise(vec2(a*19.-time*.08,r*44.+time*.15));
        float contour=.722+(n-.5)*.006;
        float core=exp(-abs(r-contour)*590.);
        float corona=exp(-abs(r-contour)*33.)*(.12+.22*n+.11*flame);
        float prominence=pow(max(0.,sin(a*3.+time*.12)+.22),3.)*.17;
        float outer=exp(-max(0.,r-contour)*13.)*smoothstep(contour,contour+.024,r)*(.04+prominence*flame);
        float asymmetry=.48+.52*smoothstep(-.8,.8,cos(a+.8));
        float tracer=exp(-abs(r-.817)*530.)*pow(max(0.,sin(a*1.5-time*.06)),18.)*.25;
        float brightness=(core*3.8+corona+outer+tracer)*asymmetry*(.65+energy*.75);
        vec3 copper=mix(vec3(1.35,.20,.035),vec3(2.1,.93,.32),core*.55);
        copper=mix(copper,mix(vec3(.035,.48,1.5),vec3(.4,1.2,2.),core*.7),spectral);
        float alpha=clamp((core+corona+outer+tracer)*2.,0.,1.);
        gl_FragColor=vec4(copper*brightness,alpha);
      }`,
  })
  const eclipse = new THREE.Mesh(new THREE.PlaneGeometry(7.6, 7.6), eclipseMaterial)
  eclipse.name = 'Awakening_eclipse'; eclipse.frustumCulled = false; scene.add(eclipse)

  let seed = 720251
  const random = () => { seed = (Math.imul(seed, 1664525) + 1013904223) | 0; return (seed >>> 0) / 4294967296 }
  const count = 2400, positions = new Float32Array(count * 3), colors = new Float32Array(count * 3), scales = new Float32Array(count)
  for (let index = 0; index < count; index++) {
    positions.set([(random() - .5) * 35, (random() - .5) * 23, (random() - .5) * 45], index * 3)
    const tint = random() > .7 ? new THREE.Color(0x71b7d5) : new THREE.Color(0xc58c61)
    colors.set(tint.toArray(), index * 3); scales[index] = .4 + random() ** 5 * 2.5
  }
  const dustGeometry = new THREE.BufferGeometry()
  dustGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3)); dustGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3)); dustGeometry.setAttribute('aScale', new THREE.BufferAttribute(scales, 1))
  const dustMaterial = new THREE.ShaderMaterial({
    uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, vertexColors: true,
    vertexShader: `uniform float time;uniform float warp;attribute float aScale;varying vec3 vColor;varying float vAlpha;void main(){vec3 p=position;p.z=mod(p.z+22.5+time*(.055+warp*8.),45.)-22.5;p.x+=sin(time*.07+position.z)*.11;vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(aScale*42./max(2.,-mv.z),.6,5.);vColor=color;vAlpha=smoothstep(1.5,5.,-mv.z)*(.25+.15*aScale);}`,
    fragmentShader: `varying vec3 vColor;varying float vAlpha;void main(){float d=length(gl_PointCoord-.5)*2.;float a=exp(-d*d*5.);if(d>1.)discard;gl_FragColor=vec4(vColor*(.5+a),a*vAlpha);}`,
  })
  const dust = new THREE.Points(dustGeometry, dustMaterial); dust.name = 'Awakening_orbital_dust'; scene.add(dust)

  const streakCount = 380, streakPositions = new Float32Array(streakCount * 6), tails = new Float32Array(streakCount * 2)
  for (let index = 0; index < streakCount; index++) {
    const p = [(random() - .5) * 32, (random() - .5) * 20, (random() - .5) * 45]
    streakPositions.set(p, index * 6); streakPositions.set(p, index * 6 + 3); tails[index * 2 + 1] = 1
  }
  const streakGeometry = new THREE.BufferGeometry()
  streakGeometry.setAttribute('position', new THREE.BufferAttribute(streakPositions, 3)); streakGeometry.setAttribute('aTail', new THREE.BufferAttribute(tails, 1))
  const streakMaterial = new THREE.ShaderMaterial({
    uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `uniform float time;uniform float warp;attribute float aTail;varying float vAlpha;void main(){vec3 p=position;p.z=mod(p.z+22.5+time*(.055+warp*8.),45.)-22.5;p.z-=aTail*(.03+warp*2.7);gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);vAlpha=(1.-aTail*.86)*warp;}`,
    fragmentShader: `varying float vAlpha;void main(){gl_FragColor=vec4(.23,.52,.8,vAlpha*.43);}`,
  })
  const streaks = new THREE.LineSegments(streakGeometry, streakMaterial); streaks.name = 'Awakening_acceleration_trails'; scene.add(streaks)

  const grade = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, time: uniforms.time, warp: uniforms.warp, strength: { value: .035 } },
    vertexShader: `varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader: `uniform sampler2D tDiffuse;uniform float time;uniform float warp;uniform float strength;varying vec2 vUv;void main(){vec2 p=vUv-.5;vec2 shift=p*.0007*warp;vec3 c=texture2D(tDiffuse,vUv).rgb;c.r=texture2D(tDiffuse,vUv+shift).r;c.b=texture2D(tDiffuse,vUv-shift).b;float vignette=1.-smoothstep(.22,.72,length(p))*.28;float noise=fract(sin(dot(vUv+mod(time,32.),vec2(12.9898,78.233)))*43758.5453)-.5;c=c*vignette+noise*strength*.06;gl_FragColor=vec4(c,1.);}`,
  })
  const forward = new THREE.Vector3(), right = new THREE.Vector3(), up = new THREE.Vector3()
  return {
    grade,
    update(time: number, energy: number, warp: number, camera: THREE.Camera, target: THREE.Vector3, inspect: boolean, spectral = 0) {
      uniforms.time.value = time; uniforms.energy.value = energy; uniforms.warp.value = warp; uniforms.spectral.value = spectral
      camera.getWorldDirection(forward); right.setFromMatrixColumn(camera.matrixWorld, 0); up.setFromMatrixColumn(camera.matrixWorld, 1)
      eclipse.position.copy(target).addScaledVector(forward, inspect ? 5.6 : 4.2).addScaledVector(right, 1.3).addScaledVector(up, .45)
      eclipse.quaternion.copy(camera.quaternion)
      eclipse.scale.setScalar(inspect ? .8 : 1)
      dust.rotation.z = Math.sin(time * .012) * .025
    },
    dispose() {
      eclipse.geometry.dispose(); eclipseMaterial.dispose(); dustGeometry.dispose(); dustMaterial.dispose(); streakGeometry.dispose(); streakMaterial.dispose(); grade.dispose()
      scene.remove(eclipse, dust, streaks)
    },
  }
}

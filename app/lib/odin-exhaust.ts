import * as THREE from 'three'

const vertexShader = `
varying vec2 vUv; varying vec3 vNormal; varying vec3 vView;
void main() {
  vUv=uv; vec4 p=modelViewMatrix*vec4(position,1.);
  vNormal=normalize(normalMatrix*normal); vView=-p.xyz;
  gl_Position=projectionMatrix*p;
}`

const fragmentShader = `
varying vec2 vUv; varying vec3 vNormal; varying vec3 vView;
uniform float time; uniform float power; uniform float layer;
void main() {
  float t=clamp(vUv.y,0.,1.);
  float facing=abs(dot(normalize(vNormal),normalize(vView)));
  float edge=pow(smoothstep(.0,.64,facing),1.35);
  float tail=pow(1.-t,1.6)*(1.-smoothstep(.84,1.,t));
  float flow=.78+.12*sin(t*33.-time*10.+sin(vUv.x*25.+time*2.))
                  +.10*sin(t*59.-time*15.-vUv.x*18.);
  vec3 blue=mix(vec3(.018,.075,.42),vec3(.16,.64,1.5),pow(1.-t,2.));
  float alpha=tail*edge*flow*.5;
  if(layer>.5 && layer<1.5) {
    blue=mix(vec3(.08,.45,1.2),vec3(.85,1.15,1.7),pow(1.-t,.7));
    alpha=tail*edge*.7;
  }
  if(layer>1.5) {
    float cells=pow(.5+.5*cos(t*31.4-time*.5),9.);
    blue=vec3(.3,.72,1.4);
    alpha=cells*tail*edge*.32;
  }
  alpha*=power;
  if(alpha<.002) discard;
  gl_FragColor=vec4(blue,alpha);
}`

export type OdinExhaust = {
  group: THREE.Group
  lightSurfaces: THREE.Object3D[]
  materials: THREE.ShaderMaterial[]
  glow: THREE.Sprite
  phase: number
}

// Open surfaces begin at y=0 (the nozzle). There are no opaque end caps or
// rectangular particle billboards; the sole sprite has a radial alpha map.
export function createOdinExhaust(radius: number, length: number, phase: number, glowTexture: THREE.Texture): OdinExhaust {
  const group = new THREE.Group(), materials: THREE.ShaderMaterial[] = []
  group.name = `Odin_exhaust_${phase}`
  for (const [layer, radialScale, axialScale] of [[0, 1.0, 1.0], [1, .36, .7], [2, .6, .85]]) {
    const material = new THREE.ShaderMaterial({
      uniforms: { time: { value: phase }, power: { value: 0 }, layer: { value: layer } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide, vertexShader, fragmentShader,
    })
    const geometry = new THREE.ConeGeometry(radius * radialScale, length * axialScale, 24, 12, true)
    geometry.translate(0, length * axialScale / 2, 0)
    const mesh = new THREE.Mesh(geometry, material)
    mesh.name = ['flowing-plume', 'bright-core', 'pressure-bands'][layer]!
    mesh.renderOrder = 2 + layer
    group.add(mesh); materials.push(material)
  }
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture, color: 0xa5ceff, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }))
  glow.position.y = .015; glow.scale.setScalar(radius * 3.4); glow.renderOrder = 5
  group.add(glow); group.rotation.x = Math.PI / 2
  group.visible = false
  return { group, materials, glow, phase, lightSurfaces: [...group.children] }
}

export function updateOdinExhaust(effect: OdinExhaust, power: number, time: number) {
  const p = THREE.MathUtils.clamp(power, 0, 1)
  effect.group.visible = p > .001
  // Group origin stays on the nozzle while the plume grows downstream.
  effect.group.scale.y = .08 + 1.07 * Math.sqrt(p) + Math.sin(time * 7 + effect.phase) * .025 * p
  effect.materials.forEach(material => {
    material.uniforms.time!.value = time + effect.phase * .73
    material.uniforms.power!.value = p
  })
  effect.glow.material.opacity = p * .7
}

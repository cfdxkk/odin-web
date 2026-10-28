import * as THREE from 'three'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'

export type FolioTreatment = 'print' | 'contour' | 'solid'

// Ink is reconstructed from lit surfaces, visible normals and depth. This is
// deliberately not a wireframe: hidden edges and coplanar triangles never print.
export function createFolioPrint(
  normal: THREE.Texture,
  depth: THREE.Texture,
  camera: THREE.PerspectiveCamera,
) {
  const pass = new ShaderPass({
    name: 'FolioEngraving',
    uniforms: {
      tDiffuse: { value: null },
      tNormal: { value: null },
      tDepth: { value: null },
      resolution: { value: new THREE.Vector2(1, 1) },
      pixelRatio: { value: 1 },
      treatmentWeights: { value: new THREE.Vector3(1, 0, 0) },
      cameraNear: { value: camera.near },
      cameraFar: { value: camera.far },
      paper: { value: new THREE.Color(0xf1f0eb) },
      ink: { value: new THREE.Color(0x293039) },
      cobalt: { value: new THREE.Color(0x2851cf) },
    },
    vertexShader: `varying vec2 vUv;
      void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
    fragmentShader: `
      precision highp float;
      varying vec2 vUv;
      uniform sampler2D tDiffuse, tNormal, tDepth;
      uniform vec2 resolution;
      uniform float pixelRatio, cameraNear, cameraFar;
      uniform vec3 treatmentWeights;
      uniform vec3 paper, ink, cobalt;
      float viewZ(float d){ return (cameraNear*cameraFar)/((cameraFar-cameraNear)*d-cameraFar); }
      float hash(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
      void main(){
        vec4 source=texture2D(tDiffuse,vUv);
        float d=texture2D(tDepth,vUv).x;
        float inside=1.-step(.999999,d);
        vec2 px=vec2(max(1.,pixelRatio*.85))/resolution;
        float dl=texture2D(tDepth,vUv-vec2(px.x,0.)).x;
        float dr=texture2D(tDepth,vUv+vec2(px.x,0.)).x;
        float du=texture2D(tDepth,vUv+vec2(0.,px.y)).x;
        float dd=texture2D(tDepth,vUv-vec2(0.,px.y)).x;
        vec3 n=normalize(texture2D(tNormal,vUv).rgb*2.-1.);
        vec3 nl=normalize(texture2D(tNormal,vUv-vec2(px.x,0.)).rgb*2.-1.);
        vec3 nr=normalize(texture2D(tNormal,vUv+vec2(px.x,0.)).rgb*2.-1.);
        vec3 nu=normalize(texture2D(tNormal,vUv+vec2(0.,px.y)).rgb*2.-1.);
        vec3 nd=normalize(texture2D(tNormal,vUv-vec2(0.,px.y)).rgb*2.-1.);
        float normalEdge=max(max(1.-dot(n,nl),1.-dot(n,nr)),max(1.-dot(n,nu),1.-dot(n,nd)));
        normalEdge=smoothstep(.11,.32,normalEdge);
        float z=viewZ(d);
        // A second derivative ignores the ordinary depth slope of a flat face.
        float curvature=max(abs(viewZ(dl)+viewZ(dr)-2.*z),abs(viewZ(du)+viewZ(dd)-2.*z));
        float depthEdge=smoothstep(.012,.045,curvature/max(.7,abs(z)*.16));
        float silhouette=step(.999999,max(max(dl,dr),max(du,dd)));
        float edge=max(silhouette,max(normalEdge*.76,depthEdge));
        float luma=pow(clamp(dot(source.rgb,vec3(.2126,.7152,.0722)),0.,1.),.4545);
        float blue=smoothstep(.025,.15,source.b-max(source.r,source.g)*1.15);
        vec2 screen=vUv*resolution/pixelRatio;
        vec2 grid=mat2(.8660254,-.5,.5,.8660254)*screen/2.6;
        vec2 cell=floor(grid);
        vec2 grain=vec2(hash(cell),hash(cell+17.3))-.5;
        float density=clamp(pow(max(0.,(.64-luma)/.50),1.55)*.84,0.,.94);
        float radius=sqrt(density)*.54*(.8+hash(cell+5.7)*.4);
        float distanceToDot=length(fract(grid)-.5+grain*.62);
        float dotInk=1.-smoothstep(radius-.065,radius+.065,distanceToDot);
        // The deepest cavities join into graphite; midtones stay visibly etched.
        float shadowInk=smoothstep(.69,.9,density);
        float coverage=mix(dotInk,1.,shadowInk*.65);
        float fiber=(hash(floor(screen*1.6))-.5)*.012;
        vec3 printed=mix(paper+fiber,ink,coverage*.92);
        printed=mix(printed,ink,edge*.88);
        printed=mix(printed,mix(paper,cobalt,.5+coverage*.5),blue*.9);
        vec3 contour=mix(paper,ink,(1.-luma)*.065);
        contour=mix(contour,ink,pow(edge,.72)*.96);
        contour=mix(contour,cobalt,blue*.7);
        vec3 solid=mix(source.rgb,ink,edge*.12);
        vec3 color=printed*treatmentWeights.x+contour*treatmentWeights.y+solid*treatmentWeights.z;
        // Additive engine light has no opaque normal/depth footprint. It remains
        // a restrained blue wash instead of becoming a rectangular ink patch.
        if(inside<.5){
          float glow=clamp(max(source.b-source.r,0.)*2.,0.,.65);
          gl_FragColor=vec4(cobalt*glow,glow);
        } else gl_FragColor=vec4(max(vec3(0.),color),max(inside,source.a));
      }`,
  })
  // ShaderPass clones ordinary uniforms; render-target textures must stay shared.
  pass.uniforms.tNormal!.value = normal
  pass.uniforms.tDepth!.value = depth
  const targetWeights = new THREE.Vector3()
  let initialized = false
  return {
    pass,
    resize(width: number, height: number, ratio: number) {
      pass.uniforms.resolution!.value.set(width * ratio, height * ratio)
      pass.uniforms.pixelRatio!.value = ratio
    },
    setTreatment(value: FolioTreatment, dt: number, immediate = false) {
      targetWeights.set(
        value === 'print' ? 1 : 0,
        value === 'contour' ? 1 : 0,
        value === 'solid' ? 1 : 0,
      )
      const weights = pass.uniforms.treatmentWeights!.value as THREE.Vector3
      if (!initialized || immediate) weights.copy(targetWeights)
      else weights.lerp(targetWeights, 1 - Math.exp(-dt * 12))
      initialized = true
      if (weights.distanceToSquared(targetWeights) < 0.00001) {
        weights.copy(targetWeights)
        return false
      }
      return true
    },
    dispose: () => pass.dispose(),
  }
}

import * as THREE from 'three'
import { ease } from './odin-motion.ts'

// All movements are authored here. The GLB contains only static, named joints.
// Model coordinates are centimeters relative to the 0.01 asset root; Blender's
// +Y (bow) maps to Three's -Z and +Z (up) maps to Three's +Y.
const rad = THREE.MathUtils.degToRad
const v = (x: number, y: number, z: number) => new THREE.Vector3(x, z, -y)
const basis = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2)
function rotation(x: number, y: number, z: number) {
  return basis.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(rad(x), rad(y), rad(z), 'XYZ'))).multiply(basis.clone().invert())
}
export function createOdinRig(root: THREE.Object3D) {
  const joints = new Map<string, { object: THREE.Object3D; position: THREE.Vector3; quaternion: THREE.Quaternion }>()
  root.traverse(object => { if (object.userData.staticJoint) joints.set(object.name, { object, position: object.position.clone(), quaternion: object.quaternion.clone() }) })
  const identity = new THREE.Quaternion()
  const followers: { object: THREE.Object3D; shroud: THREE.Object3D; relative: THREE.Matrix4; stowDelta: THREE.Vector3 }[] = []
  const targetMatrix = new THREE.Matrix4(), localMatrix = new THREE.Matrix4(), rigidScale = new THREE.Vector3()
  const pose = (name: string, move: THREE.Vector3, turn = identity) => {
    const joint = joints.get(name); if (!joint) return
    joint.object.position.copy(joint.position).add(move)
    joint.object.quaternion.copy(turn).multiply(joint.quaternion)
  }
  function apply(deployment: number, time: number) {
    const d = THREE.MathUtils.clamp(deployment, 0, 1)
    // All five armor pieces clear the bore corridor before any gun movement.
    // The long skins translate to their exposed outboard resting position;
    // aft fillers turn around the fixed hull lips, and the nose lifts over its
    // seal before sliding toward the bow. Reverse evaluation lowers the guns
    // completely before the armor closes around them.
    const covers = ease(0, .34, d)
    // One mechanical stroke drives the armored cradle, covers and complete
    // bores. Independent easing previously made the centre gun dip and rebound.
    const barrels = ease(.46, .93, d)
    const lift = ease(.52, .93, d)
    const sideSeat = ease(.34, .44, d)
    const aim = ease(.95, 1, d)
    for (const side of ['Dorsal', 'Ventral']) {
      const sign = side === 'Dorsal' ? 1 : -1
      const mountRise = side === 'Dorsal' ? 2.311 : 3.137
      // Moving the parent keeps the circular base, armored housing and bore
      // guides together rather than letting their separate joints drift apart.
      pose(`Main_${side}_Mount`, v(0, (2 + (side === 'Ventral' ? .274 : 0)) * barrels, sign * mountRise * barrels))
      pose(`Main_${side}_Housing`, v(0, 0, 0))
      const cradle = -3 + 8.803 * barrels
      pose(`Main_${side}_Barrels`, v(0, (2.8 + (side === 'Ventral' ? .506 : 0)) * barrels, sign * cradle), rotation(sign * 11 * barrels, 0, 0))
      // Only used to capture the original closed and fully deployed reference
      // poses at initialization. Runtime followers below solve the rigid link.
      if (!followers.length) for (const role of ['Port', 'Center', 'Starboard']) {
        const name = `Main_${side}_Carrier_${role}`, carrier = joints.get(name)?.object.userData
        if (carrier?.stowOffset) {
          const move = v(...carrier.stowOffset as [number, number, number]).multiplyScalar(1 - barrels)
          pose(name, move)
        }
      }
      for (const [role, offset] of [['Port', -2], ['Center', 0], ['Starboard', 2]] as const) {
        const shroudTravel = role === 'Center' ? -2.118 : 3.009
        pose(`Main_${side}_Shroud_${role}`, v(offset * sign * barrels, .60 * barrels, sign * shroudTravel * barrels), rotation(sign * 11 * barrels, 0, 0))
      }
      for (const leaf of ['Port', 'Starboard']) {
        const name = `Hatch_${side}_${leaf}`
        const data = joints.get(name)?.object.userData
        // First lift just clear of the serrated lip, then ease outboard and
        // down to the exposed resting position. The rigid skin never rotates.
        if (data?.clearanceLift && data?.slideVector) {
          const liftOff = ease(0, .14, covers), travel = ease(.10, 1, covers)
          const settle = travel * travel
          const clearance = data.clearanceLift as [number, number, number]
          const slide = data.slideVector as [number, number, number]
          // Release the close-fitting aft scarf before crossing its hinged lip.
          const earlyRelease = Number(data.earlySeamReleaseFraction || 0)
          const seamRelease = Number(data.seamReleaseVector?.[1] || 0) * (
            earlyRelease * ease(0, .06, d) + (1 - earlyRelease) * ease(.10, .20, d))
          pose(name, v(slide[0] * travel, slide[1] * travel + seamRelease, clearance[2] * liftOff * (1 - settle) + slide[2] * settle))
        }
        // The aft fillers fold out and down about the sloped fixed hull lip.
        // Their pivots stay anchored instead of sliding with the armor skin.
        const aftName = `Hatch_${side}_Aft_${leaf}`, aft = joints.get(aftName)?.object.userData
        if (aft?.hingeAxis && Number.isFinite(aft.openingAngleDegrees)) {
          const axis = aft.hingeAxis as [number, number, number]
          const turn = new THREE.Quaternion().setFromAxisAngle(v(...axis).normalize(), rad(Number(aft.openingAngleDegrees)) * ease(.14, .32, d))
          pose(aftName, v(0, 0, 0), turn)
        }
      }
      // All three tubes telescope together after the armor and gun bodies
      // clear. Each follows its measured bore axis; the deployed endpoints
      // stay fixed, and reversing nests the tubes before the armor closes.
      const extend = ease(.66, .93, d)
      for (const role of ['Port', 'Center', 'Starboard']) {
        const tubeName = `Main_${side}_Tube_${role}`, tube = joints.get(tubeName)?.object.userData
        if (tube?.boreAxis && tube?.deployedOffset && Number.isFinite(tube.stowTravel)) {
          const axis = tube.boreAxis as [number, number, number]
          const end = tube.deployedOffset as [number, number, number]
          pose(tubeName, v(...end).addScaledVector(v(...axis).normalize(), -Number(tube.stowTravel) * (1 - extend)))
        }
      }
      const noseName = `Hatch_${side}_Nose`, nose = joints.get(noseName)?.object.userData
      if (nose?.liftVector && nose?.slideVector) {
        const raise = ease(0, .10, d), forward = ease(.10, .31, d)
        const a = nose.liftVector as [number, number, number], b = nose.slideVector as [number, number, number]
        pose(noseName, v(a[0] * raise + b[0] * forward, a[1] * raise + b[1] * forward, a[2] * raise + b[2] * forward))
      }
    }
    // Keep each complete bore at its deployed rigid offset from its own cover.
    // On closing, both side covers first reach their seat; only then do their
    // bores descend the last short distance. The centre never leaves its cover.
    for (const follower of followers) {
      const { object, shroud, relative, stowDelta } = follower
      shroud.updateWorldMatrix(true, false)
      object.parent!.updateWorldMatrix(true, false)
      targetMatrix.copy(relative)
      targetMatrix.elements[12] += stowDelta.x * (1 - sideSeat)
      targetMatrix.elements[13] += stowDelta.y * (1 - sideSeat)
      targetMatrix.elements[14] += stowDelta.z * (1 - sideSeat)
      localMatrix.copy(object.parent!.matrixWorld).invert().multiply(shroud.matrixWorld).multiply(targetMatrix)
      localMatrix.decompose(object.position, object.quaternion, rigidScale)
    }
    const axialShutters = ease(.08, .35, d)
    for (const station of ['Bow', 'Stern', 'Keel']) for (const leaf of ['Port', 'Starboard']) {
      const name = `Axial_${station}_Shutter_${leaf}`, data = joints.get(name)?.object.userData
      if (data?.hingeAxis) pose(name, v(0, 0, 0), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(...data.hingeAxis as [number, number, number]).normalize(), rad(Number(data.openingSign) * 90 * (1 - axialShutters))))
    }
    const axial = ease(.38, .84, d)
    pose('Axial_Bow_Barrel', v(0, .432 * axial, -.399 * axial - 5.2 * (1 - axial)), rotation(21 * axial, 0, 0))
    pose('Axial_Stern_Barrel', v(0, -.276 * axial, -.505 * axial - 5.2 * (1 - axial)), rotation(-21 * axial, 0, 0))
    pose('Axial_Keel_Mount', v(0, 14.270 * lift, -6.135 * lift))
    pose('Axial_Keel_Barrel', v(0, -.386 * axial, .444 * axial + 5.2 * (1 - axial)), rotation(21 * axial, 0, 0))
    for (let index = 0; index < 4; index++) {
      const unfold = ease(.16 + index * .025, .77 + index * .025, d)
      for (const [side, sign] of [['Port', -1], ['Starboard', 1]] as const) {
        const name = `SideBattery_${index + 1}_${side}`
        const data = joints.get(name)?.object.userData.deployQuaternion
        if (!data) continue
        const scan = Math.sin(time * .11 + index * .85 + sign) * 5 * aim
        const turn = identity.clone().slerp(new THREE.Quaternion(...data as [number, number, number, number]), unfold)
        pose(name, v(0, 0, 0), rotation(0, 0, scan).multiply(turn))
      }
    }
    const carriage = ease(.06, .37, d), ring = ease(.31, .60, d), gun = ease(.57, .91, d)
    for (const station of ['Forward', 'Aft']) for (const [side, sign] of [['Port', -1], ['Starboard', 1]] as const) {
      pose(`DefenseRail_${station}_${side}`, v(sign * (station === 'Forward' ? 9.781 : 9.903) * carriage, (station === 'Forward' ? 2.079 : -1.392) * carriage, 0))
    }
    for (let i = 0; i < 8; i++) {
      const prefix = `Defense_${String(i + 1).padStart(2, '0')}`, data = joints.get(prefix + '_Carriage')?.object.userData
      const sign = Number(data?.side || 1), forward = i < 4
      pose(prefix + '_Carriage', v(sign * (forward ? 9.781 : 9.903) * carriage, (forward ? 2.079 : -1.392) * carriage, 2 * ring))
      pose(prefix + '_Yaw', v(0, 0, 0), rotation(0, 0, sign * 35 * gun))
      const axis = joints.get(prefix + '_Elevation')?.object.userData.hingeAxis
      if (axis) pose(prefix + '_Elevation', v(0, 0, 0), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(...axis as [number, number, number]), rad(25 * gun)))
    }
    // The RSI tower-quad clip shows parallel gun rails, not a 180-degree flip.
    // A short pod travel precedes the longer gun slide; yaw begins only in SCM.
    const pdcOut = ease(.10, .40, d), pdcArms = ease(.36, .88, d)
    for (const [side, sign] of [['Port', -1], ['Starboard', 1]] as const) {
      pose(`PDC_${side}_Carriage`, v(sign * (12 + 8 * pdcOut), 0, 0))
      pose(`PDC_${side}_Gimbal`, v(0, 0, 0), rotation(0, 0, Math.sin(time * .10 + sign) * 8 * aim))
      for (let i = 0; i < 4; i++) {
        const armOpen = ease(.36 + (i >= 2 ? .025 : 0), .86 + (i >= 2 ? .025 : 0), d)
        pose(`PDC_${side}_Arm_${i}`, v(-sign * 20 * (1 - armOpen), 0, 0))
      }
    }
    // Existing bridge louvers follow the roof guide before rotating into place.
    const shield = ease(.04, .56, d)
    joints.forEach(({ object }, name) => {
      if (!name.startsWith('BridgeArmor_')) return
      const bank = object.userData.bank
      if (bank === 'Front') {
        const slide = ease(0, .50, shield), fold = ease(.25, 1, shield)
        pose(name, v(0, -5 * (1 - slide), 1.50 * (1 - fold)), rotation(-55 * (1 - fold), 0, 0))
      }
      if (bank === 'RearUpper') pose(name, v(0, -.32 * shield, 0), rotation(-82 * shield, 0, 0))
      if (bank === 'RearLower') pose(name, v(0, -.24 * shield, 0), rotation(77 * shield, 0, 0))
    })
    return { joints: joints.size, deployment: d, covers, barrels, pdcArms, shield }
  }
  // Capture the unchanged fully deployed attachment once. The ventral source
  // cover names are mirrored relative to their physical port/starboard bores.
  apply(1, 0)
  root.updateWorldMatrix(true, true)
  const references = [] as typeof followers
  for (const bank of ['Dorsal', 'Ventral']) for (const role of ['Port', 'Center', 'Starboard']) {
    const object = joints.get(`Main_${bank}_Carrier_${role}`)?.object
    const coverRole = bank === 'Ventral' && role !== 'Center' ? (role === 'Port' ? 'Starboard' : 'Port') : role
    const shroud = joints.get(object?.userData.followShroud || `Main_${bank}_Shroud_${coverRole}`)?.object
    if (object && shroud) references.push({ object, shroud, relative: shroud.matrixWorld.clone().invert().multiply(object.matrixWorld), stowDelta: new THREE.Vector3() })
  }
  apply(0, 0)
  root.updateWorldMatrix(true, true)
  for (const follower of references) {
    if (!follower.object.name.endsWith('_Center')) {
      const closed = follower.shroud.matrixWorld.clone().invert().multiply(follower.object.matrixWorld)
      follower.stowDelta.setFromMatrixPosition(closed).sub(new THREE.Vector3().setFromMatrixPosition(follower.relative))
    }
  }
  followers.push(...references)
  for (const { object, position, quaternion } of joints.values()) {
    object.position.copy(position); object.quaternion.copy(quaternion)
  }
  root.updateWorldMatrix(true, true)
  return { apply, jointCount: joints.size }
}

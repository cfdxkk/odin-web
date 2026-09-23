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
  const pose = (name: string, move: THREE.Vector3, turn = identity) => {
    const joint = joints.get(name); if (!joint) return
    joint.object.position.copy(joint.position).add(move)
    joint.object.quaternion.copy(turn).multiply(joint.quaternion)
  }
  function apply(deployment: number, time: number) {
    const d = THREE.MathUtils.clamp(deployment, 0, 1)
    const covers = ease(0, .28, d)
    const lift = ease(.32, .61, d)
    const barrels = ease(.48, .82, d)
    const aim = ease(.95, 1, d)
    // Guns return to the neutral axis before lowering; plates close last.
    for (const side of ['Dorsal', 'Ventral']) {
      const sign = side === 'Dorsal' ? 1 : -1
      pose(`Main_${side}_Mount`, v(0, 0, 0))
      pose(`Main_${side}_Housing`, v(0, side === 'Ventral' ? .274 * lift : 0, sign * (side === 'Dorsal' ? 2.311 : 3.137) * lift))
      pose(`Main_${side}_Barrels`, v(0, side === 'Ventral' ? .780 * lift : 0, sign * (side === 'Dorsal' ? 8.114 : 8.918) * lift), rotation(sign * 11 * barrels, 0, 0))
      for (const [role, offset] of [['Port', -2], ['Center', 0], ['Starboard', 2]] as const) {
        const travel = role === 'Center' ? (side === 'Dorsal' ? .193 : .973) : (side === 'Dorsal' ? 5.321 : 6.083)
        pose(`Main_${side}_Shroud_${role}`, v(offset * sign * lift, .60 * lift, sign * travel * lift), rotation(sign * 11 * barrels, 0, 0))
      }
      for (let i = 0; i < 5; i++) {
        for (const leaf of ['Port', 'Starboard']) {
          const name = `Hatch_${side}_${leaf}_${String(i).padStart(2, '0')}`
          const data = joints.get(name)?.object.userData
          if (!data?.hingeAxis) continue
          const open = ease(i * .009, .24 + i * .009, d)
          pose(name, v(0, 0, 0), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(...data.hingeAxis as [number, number, number]).normalize(), rad(Number(data.openingSign) * 172 * open)))
        }
      }
    }
    const axial = ease(.24, .76, d)
    pose('Axial_Bow_Barrel', v(0, .432 * axial, -.399 * axial), rotation(21 * axial, 0, 0))
    pose('Axial_Stern_Barrel', v(0, -.276 * axial, -.505 * axial), rotation(-21 * axial, 0, 0))
    pose('Axial_Keel_Mount', v(0, 14.270 * lift, -6.135 * lift))
    pose('Axial_Keel_Barrel', v(0, -.386 * axial, .444 * axial), rotation(21 * axial, 0, 0))
    const sideAngles = [[-2.45, 1.47, -30.97], [30.45, .18, -11.55], [-2.53, 1.71, -33.96], [26.59, -17.91, -1.24]]
    for (let index = 0; index < 4; index++) {
      const unfold = ease(.16 + index * .025, .77 + index * .025, d)
      for (const [side, sign] of [['Port', -1], ['Starboard', 1]] as const) {
        const [x, y, z] = sideAngles[index]!
        const scan = Math.sin(time * .11 + index * .85) * 7 * aim
        pose(`SideBattery_${index + 1}_${side}`, v(0, 0, 0), rotation(0, 0, scan).multiply(rotation(x! * unfold, y! * sign * unfold, z! * sign * unfold)))
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
    // Tower PDCs: withdraw the folded gun arms behind the armored pod, slide the
    // carriage clear of the tower, then unfold opposing arms around separate hinges.
    const pdcOut = ease(.10, .42, d), pdcArms = ease(.46, .90, d)
    for (const [side, sign] of [['Port', -1], ['Starboard', 1]] as const) {
      pose(`PDC_${side}_Carriage`, v(sign * 20 * pdcOut, 0, 0))
      pose(`PDC_${side}_Gimbal`, v(0, 0, 0), rotation(0, 0, Math.sin(time * .10 + sign) * 8 * aim))
      for (let i = 0; i < 4; i++) {
        const upper = i % 2 === 1
        const armOpen = ease(.46 + (i >= 2 ? .035 : 0), .88 + (i >= 2 ? .035 : 0), d)
        pose(`PDC_${side}_Arm_${i}`, v(0, 0, 0), rotation(0, sign * (upper ? -1 : 1) * 180 * (1 - armOpen), 0))
      }
    }
    // Existing bridge louvers follow the roof guide before rotating into place.
    const shield = ease(.04, .56, d)
    joints.forEach(({ object }, name) => {
      if (!name.startsWith('BridgeArmor_')) return
      const bank = object.userData.bank
      if (bank === 'Front') pose(name, v(0, 5.2 * ease(0, .40, shield), 0), rotation(57 * ease(.30, 1, shield), 0, 0))
      if (bank === 'RearUpper') pose(name, v(0, -.32 * shield, 0), rotation(-82 * shield, 0, 0))
      if (bank === 'RearLower') pose(name, v(0, -.24 * shield, 0), rotation(77 * shield, 0, 0))
    })
    return { joints: joints.size, deployment: d, covers, barrels, pdcArms, shield }
  }
  return { apply, jointCount: joints.size }
}

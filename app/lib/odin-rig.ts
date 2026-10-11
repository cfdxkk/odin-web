import * as THREE from 'three'
import { ease } from './odin-motion.ts'
import { bowSourceMotion } from './bow-source-motion.ts'
import { sternSourceMotion } from './stern-source-motion.ts'
import { flankSourceMotion } from './flank-source-motion.ts'
import { bridgeQuadCarriageAmount, bridgeQuadSourceAim, bridgeQuadCompactAmount, bridgeQuadPetalAmount, bridgeQuadTubeCompactAmount, bridgeQuadTubeCompactVector, bridgeQuadBearingCompactVector, bridgeQuadGuideCompactVector, bridgeQuadTubeSlideAmount, bridgeQuadTubeSlideVector } from './bridge-quad-source-motion.ts'
import { turretPoseProgress } from './turret-tempo.ts'

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
  const bowJoint = joints.get('Axial_Bow_Barrel')?.object
  const bowMount = joints.get('Axial_Bow_Mount')?.object
  const bowRestWeb = bowJoint && bowMount ? bowJoint.position.clone().add(bowMount.position) : undefined
  const sternJoint = joints.get('Axial_Stern_Barrel')?.object
  const sternMount = joints.get('Axial_Stern_Mount')?.object
  const sternRestWeb = sternJoint && sternMount ? sternJoint.position.clone().add(sternMount.position) : undefined
  function apply(deployment: number, time: number) {
    const d = THREE.MathUtils.clamp(deployment, 0, 1)
    const quadProgress = turretPoseProgress(d, 'quad')
    const aftProgress = turretPoseProgress(d, 'aftTwin')
    // All five armor pieces clear the bore corridor before any gun movement.
    // The long skins translate to their exposed outboard resting position;
    // aft fillers turn around the fixed hull lips, and the nose lifts over its
    // seal before sliding toward the bow. Reverse evaluation lowers the guns
    // completely before the armor closes around them.
    const covers = ease(0, .34, d)
    // One mechanical stroke drives the armored cradle, covers and complete
    // bores. Independent easing previously made the centre gun dip and rebound.
    const barrels = ease(.40, .93, d)
    const lift = ease(.52, .93, d)
    // Overlap the short seating stroke with the cradle's acceleration: the
    // outer bores must never finish one lift and wait for the next to start.
    const sideSeat = ease(.34, .56, d)
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
          const liftOff = ease(0, Number(data.clearancePhaseEnd || .14), covers), travel = ease(.10, 1, covers)
          const settle = travel * travel
          const clearance = data.clearanceLift as [number, number, number]
          const slide = data.slideVector as [number, number, number]
          // Release the close-fitting aft scarf before crossing its hinged lip.
          const earlyRelease = Number(data.earlySeamReleaseFraction || 0)
          const seamRelease = Number(data.seamReleaseVector?.[1] || 0) * (
            earlyRelease * ease(side === 'Dorsal' ? .02 : 0, .06, d) + (1 - earlyRelease) * ease(.10, .20, d))
          pose(name, v(slide[0] * travel, slide[1] * travel + seamRelease, clearance[2] * liftOff * (1 - settle) + slide[2] * settle))
        }
        // The aft fillers fold out and down about the sloped fixed hull lip.
        // Their pivots stay anchored instead of sliding with the armor skin.
        const aftName = `Hatch_${side}_Aft_${leaf}`, aft = joints.get(aftName)?.object.userData
        if (aft?.hingeAxis && Number.isFinite(aft.openingAngleDegrees)) {
          const axis = aft.hingeAxis as [number, number, number]
          const fold = side === 'Dorsal' ? ease(.20, .32, d) : ease(.14, .32, d)
          const turn = new THREE.Quaternion().setFromAxisAngle(v(...axis).normalize(), rad(Number(aft.openingAngleDegrees)) * fold)
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
        const raise = ease(0, side === 'Dorsal' ? .035 : .10, d), forward = ease(side === 'Dorsal' ? .07 : .10, .31, d)
        const a = nose.liftVector as [number, number, number], b = nose.slideVector as [number, number, number]
        pose(noseName, v(a[0] * raise + b[0] * forward, a[1] * raise + b[1] * forward, a[2] * raise + b[2] * forward))
      }
    }
    // Keep each complete bore at its deployed rigid offset from its own cover.
    // Closing blends continuously into the short final sink, which finishes
    // after the covers seat. The centre never leaves its own cover.
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
    // Eleven singles: one physical pitch axis per bore, no yaw or idle scan.
    // Every pair of vented skins closes into the channel's triangular cap.
    const singleLift = ease(.39, .84, d)
    joints.forEach(({ object }, name) => {
      const data = object.userData
      if (data.barrelJoint && data.hingeAxisModel) {
        const leafOpen = ease(Number(data.openStart ?? .02), Number(data.openEnd ?? .30), d)
        const closed = Number(data.closedAngleDegrees)
        const openingTravel = Number(data.openingTravelDegrees ?? Math.abs(closed))
        const angle = closed - Math.sign(closed) * openingTravel * leafOpen
        pose(name, v(0, 0, 0), new THREE.Quaternion().setFromAxisAngle(v(...data.hingeAxisModel as [number, number, number]).normalize(), rad(angle)))
      }
      if (data.singleBattery && data.hingeAxisModel) {
        if (name === 'Axial_Bow_Barrel' && bowRestWeb) {
          const { move, turn } = bowSourceMotion(d, bowRestWeb)
          pose(name, move, turn)
        } else if (name === 'Axial_Stern_Barrel' && sternRestWeb) {
          const { move, turn } = sternSourceMotion(d, sternRestWeb)
          pose(name, move, turn)
        } else if (data.sourceEulerMotion) {
          pose(name, v(0, 0, 0), flankSourceMotion(data, d))
        } else {
          const gunLift = data.sideBatteryMechanism || data.stagedSingleBattery ? ease(.67, .96, d) : singleLift
          const seatAxis = (data.stowDirectionModel || data.outwardNormal) as [number, number, number]
          const seating = v(...seatAxis).multiplyScalar(-Number(data.stowSink || 0) * (1 - gunLift))
          const restLift = Number(data.restLiftDegrees || 0)
          pose(name, seating, new THREE.Quaternion().setFromAxisAngle(v(...data.hingeAxisModel as [number, number, number]).normalize(), rad(restLift * (1 - gunLift) + Number(data.pitchDegrees) * gunLift)))
        }
      }
      if (data.system === 'side-front-slider') {
        // This pair is authored CLOSED: lift off its seal, then slide forward.
        pose(name, v(...data.liftVector as [number, number, number]).multiplyScalar(ease(0, .07, d))
          .add(v(...data.slideVector as [number, number, number]).multiplyScalar(ease(.08, .24, d))))
      }
      if (data.system === 'side-battery-carriage') {
        // Closing first folds the leaves, then lifts the complete rear cradle
        // and advances it until groups 3/4 seat against stationary group 2.
        const closing = 1 - d
        pose(name, v(...data.liftVector as [number, number, number]).multiplyScalar(ease(.76, .86, closing))
          .add(v(...data.slideVector as [number, number, number]).multiplyScalar(ease(.87, 1, closing))))
      }
      if (data.system === 'single-source-carriage') {
        // The source rear pair and bore share this physical turret shell.
        // Reversing stows the bore first, seats the shell, then shuts armor.
        const rise = ease(Number(data.raiseStart), Number(data.raiseEnd), d)
        pose(name, v(...data.closedOffsetModel as [number, number, number]).multiplyScalar(1 - rise))
      }
      if (data.system === 'single-front-cap') {
        if (data.sourceCapStroke) {
          // The source shell stays rigid: lift off the original receiver,
          // advance over it. The side 2/4 caps hold their raised position.
          const raised = ease(0, Number(data.releaseEnd ?? .08), d)
          const forward = ease(Number(data.slideStart ?? .10), Number(data.slideEnd ?? .23), d)
          const parked = data.holdRaisedAfterAdvance ? 0 : ease(Number(data.settleStart ?? .24), Number(data.settleEnd ?? .26), d)
          pose(name, v(...data.slideVector as [number, number, number])
            .addScaledVector(v(...data.clearanceLiftVector as [number, number, number]), raised)
            .addScaledVector(v(...data.advanceVector as [number, number, number]), forward)
            .addScaledVector(v(...data.parkingSettleVector as [number, number, number]), parked))
          return
        }
        // Recovered source caps are authored in their deployed location.
        // NAV seats them against the folding leaves; SCM returns to source.
        const slide = ease(Number(data.slideStart ?? .09), Number(data.slideEnd ?? .23), d)
        const settle = ease(Number(data.settleStart ?? .24), Number(data.settleEnd ?? .36), d)
        pose(name, v(...data.slideVector as [number, number, number]).multiplyScalar(data.sourceOpenPose ? 1 - slide : slide)
          .add(v(...data.settleVector as [number, number, number]).multiplyScalar(data.sourceOpenPose ? 1 - settle : settle)))
      }
      if (data.system === 'pdc-hull-petal') {
        const center = data.sourceCenteredPetal ? bridgeQuadCompactAmount(data, quadProgress) : 1 - ease(Number(data.compactStart ?? .03), Number(data.compactEnd ?? .14), quadProgress)
        const compact = data.translationOnly ? bridgeQuadPetalAmount(data, quadProgress) : center
        const move = v(...(data.sourceQuadPetal ? data.compactVector : data.stowVector) as [number, number, number]).multiplyScalar(compact)
        if (data.translationOnly) {
          // Lock ship X (port/starboard in plan view) for every vertex:
          // no petal rotation or inherited aiming/carriage motion is applied.
          move.x = 0
          pose(name, move)
          return
        }
        if (data.clearanceVector) move.add(v(...data.clearanceVector as [number, number, number])
          .multiplyScalar((1 - ease(Number(data.clearanceStart), Number(data.clearanceEnd), quadProgress)) * (1 - compact ** 3)))
        let turn = identity
        if (data.compactRotationWXYZ) {
          const [w,x,y,z] = data.compactRotationWXYZ as number[]
          const alignment = data.sourceCenteredPetal ? 1 - ease(Number(data.alignStart), Number(data.alignEnd), quadProgress) : compact
          const modelTurn = new THREE.Quaternion().slerp(new THREE.Quaternion(x,y,z,w).normalize(), alignment)
          turn = basis.clone().multiply(modelTurn).multiply(basis.clone().invert())
        }
        pose(name, move, turn)
      }
    })
    // The keel mount is baked at the former 14% carriage position. Only its
    // seven armor covers and barrel articulate; the complete bay stays fixed.
    // Aft cover release, complete carriage travel and aiming share a retimed
    // clock. Reversing still seats the gun and rails before the gates close.
    const aftFinal = ease(.05, .20, aftProgress)
    const aftCarriage = .2 * aftFinal + .8 * ease(.20, .52, aftProgress)
    const aftSink = 1 - ease(.05, .40, aftProgress)
    const gate = ease(0, .05, aftProgress), carriage = ease(.24, .52, d), gun = ease(.65, .94, aftProgress)
    for (let i = 5; i <= 8; i++) {
      const name = `Defense_${String(i).padStart(2, '0')}_NotchGate`, data = joints.get(name)?.object.userData
      if (data?.slideVector) pose(name, v(...data.slideVector as [number, number, number]).multiplyScalar(gate).add(v(...data.releaseVector as [number, number, number]).multiplyScalar(ease(0, .04, aftProgress))))
    }
    for (const station of ['Forward', 'Aft']) for (const [side, sign] of [['Port', -1], ['Starboard', 1]] as const) {
      const name = `DefenseRail_${station}_${side}`
      const railData = joints.get(name)?.object.userData
      if (railData?.guidesFollowCompleteCarriage) { pose(name, v(0, 0, 0)); continue }
      const drop = station === 'Aft' ? Number(railData?.finalStowDrop || 0) * aftSink
        : Number(railData?.stowDrop || 0) * (1 - ease(Number(railData?.raiseStart ?? .52), Number(railData?.raiseEnd ?? .68), d))
      // The long guides and lower brackets retract a little behind the gun,
      // but travel to the same inboard seat. The former shorter travel left
      // them protruding through the turret glazing during the stroke.
      const aftRailInboard = station === 'Aft'
        ? aftCarriage + Number(railData?.retractLag || 0) * Math.sin(Math.PI * aftCarriage)
        : 0
      const aftRailExtra = Number(railData?.finalStowInward || 0)
      pose(name, station === 'Aft'
        ? v(sign * ((9.903 + aftRailExtra) * aftRailInboard - aftRailExtra), -1.392 * aftRailInboard, -drop)
        : v(sign * 9.781 * carriage, 2.079 * carriage, -drop))
    }
    for (let i = 0; i < 8; i++) {
      const prefix = `Defense_${String(i + 1).padStart(2, '0')}`, data = joints.get(prefix + '_Carriage')?.object.userData
      const sign = Number(data?.side || 1), forward = i < 4
      const inward = forward ? 0 : Number(data?.finalStowInward || 0)
      const finalSink = forward ? 0 : Number(data?.finalStowDrop || 0) * aftSink
      const gunMotion = forward ? ease(Number(data?.aimStart ?? .69), .94, d) : gun
      if (forward && data?.inclinedStow) {
        // The cradle slides along its stationary lower foundation. Alignment
        // is a fixed installation angle, never a late rotation during travel.
        const seated = 1 - ease(Number(data.travelStart), Number(data.travelEnd), d)
        const move = v(...data.deployedOffsetModel as [number, number, number])
          .addScaledVector(v(...data.stowVectorModel as [number, number, number]), seated)
        const alignment = Number(data.fixedInstallationDegrees ?? data.closedAlignmentDegrees ?? 0)
        pose(prefix + '_Carriage', move, rotation(0, 0, alignment))
        // Source guides retain the receiver heading at every progress value.
        if (joints.get(prefix + '_Guides')?.object.userData.preserveReceiverHeading)
          pose(prefix + '_Guides', v(0, 0, 0), rotation(0, 0, -alignment))
        // Once the carriage seats, only original tube surfaces withdraw along
        // their horizontal bore axes. Rear elevation brackets stay on the gun.
        const tubeName = prefix + '_Tubes', tube = joints.get(tubeName)?.object.userData
        if (tube) pose(tubeName, v(...tube.horizontalBoreAxisModel as [number, number, number])
          .multiplyScalar(-Number(tube.stowTravel) * (1 - ease(Number(tube.extendStart), Number(tube.extendEnd), d))))
      } else {
        const forwardSink = forward ? Number(data?.stowDrop || 0) * (1 - ease(Number(data?.raiseStart ?? .52), Number(data?.raiseEnd ?? .68), d)) : 0
        pose(prefix + '_Carriage', forward
          ? v(sign * 9.781 * carriage, 2.079 * carriage, -forwardSink)
          : v(sign * ((9.903 + inward) * aftCarriage - inward), -1.392 * aftCarriage, -finalSink))
      }
      const heading = [16, -12, 16, -12, 22, -16, 22, -16][i]!
      const scan = Math.sin(time * .10 + i * .7) * 3 * (forward ? aim : ease(.95, 1, aftProgress))
      pose(prefix + '_Yaw', v(0, 0, 0), rotation(0, 0, sign * heading * gunMotion + scan))
      const elevation = joints.get(prefix + '_Elevation')?.object.userData
      const axis = elevation?.hingeAxisModel
      if (axis) pose(prefix + '_Elevation', v(0, 0, 0), new THREE.Quaternion().setFromAxisAngle(v(...axis as [number, number, number]).normalize(), rad(Number(elevation.pitchDegrees)) * gunMotion))
    }
    // Restore the complete original bridge quads and their source carriage/aim
    // curves. Closing neutralizes aim and seats the turret at source frame 30,
    // then withdraws the tubes before the cradles and petals close together.
    // Opening releases each cradle with its own petal first, then extends tubes.
    const pdcArms = ease(.03, .18, quadProgress)
    for (const [side, sign] of [['Port', -1], ['Starboard', 1]] as const) {
      const carriageName = `PDC_${side}_Carriage`, carriageData = joints.get(carriageName)?.object.userData
      if (carriageData?.sourceQuadCarriage) {
        const closed = v(...carriageData.sourceClosedOrigin as [number, number, number])
        const deployed = v(...carriageData.sourceDeployedOrigin as [number, number, number])
        pose(carriageName, closed.sub(deployed).multiplyScalar(1 - bridgeQuadCarriageAmount(carriageData, quadProgress)))
      } else pose(carriageName, v(sign * (18 + 2 * ease(.10, .40, quadProgress)), 0, 0))
      const gimbalName = `PDC_${side}_Gimbal`, gimbalData = joints.get(gimbalName)?.object.userData
      pose(gimbalName, v(0, 0, 0), gimbalData?.sourceQuadAim
        ? bridgeQuadSourceAim(gimbalData, quadProgress) : rotation(0, 0, Math.sin(time * .10 + sign) * 8 * aim))
      for (let i = 0; i < 4; i++) {
        const cradleName = `PDC_${side}_Cradle_${i}`, cradleData = joints.get(cradleName)?.object.userData
        if (cradleData?.quadCompact) pose(cradleName, v(...bridgeQuadBearingCompactVector(cradleData))
          .multiplyScalar(bridgeQuadTubeCompactAmount(cradleData, quadProgress)))
        const guideName = `PDC_${side}_CradleGuide_${i}`, guideData = joints.get(guideName)?.object.userData
        if (guideData && cradleData) pose(guideName, v(...bridgeQuadGuideCompactVector(cradleData, guideData))
          .multiplyScalar(bridgeQuadTubeCompactAmount(guideData, quadProgress)))
        const armName = `PDC_${side}_Arm_${i}`, armData = joints.get(armName)?.object.userData
        const armOpen = armData?.sourceFullTube ? 1 - bridgeQuadTubeSlideAmount(d)
          : ease(Number(armData?.slideStart ?? .36), Number(armData?.slideEnd ?? .88), quadProgress)
        const slide = armData?.sourceFullTube ? bridgeQuadTubeSlideVector(armData)
          : armData?.slideVector ?? [-sign * Number(armData?.stowTravel || 13.5), 0, 0]
        const move = v(...slide as [number, number, number]).multiplyScalar(1 - armOpen)
        if (armData?.sourceFullTube && cradleData?.quadCompact) {
          const tubePacking = v(...bridgeQuadTubeCompactVector(cradleData))
          const bearingPacking = v(...bridgeQuadBearingCompactVector(cradleData))
          move.add(tubePacking.sub(bearingPacking).multiplyScalar(bridgeQuadTubeCompactAmount(cradleData, quadProgress)))
        }
        pose(armName, move)
      }
    }
    return { joints: joints.size, deployment: d, covers, barrels, pdcArms }
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
      // Keep the original inward nesting, but halve the excessive depth under
      // the cover. At rest these shroud axes match the asset's glTF axes (+Y up).
      follower.stowDelta.y *= .5
    }
  }
  followers.push(...references)
  for (const { object, position, quaternion } of joints.values()) {
    object.position.copy(position); object.quaternion.copy(quaternion)
  }
  root.updateWorldMatrix(true, true)
  return { apply, jointCount: joints.size }
}

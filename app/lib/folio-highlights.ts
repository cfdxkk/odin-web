import { classifyWeaponJoint, type WeaponGroup } from './odin-weapon-groups.ts'

type RigNode = {
  name: string
  userData: { staticJoint?: unknown }
  parent: RigNode | null
}

export function folioWeaponGroup(
  object: RigNode,
  root?: RigNode,
): WeaponGroup | undefined {
  for (
    let node: RigNode | null = object;
    node && node !== root;
    node = node.parent
  ) {
    // GLTFLoader names primitive meshes from the Blender mesh datablock. The
    // merged hull's datablock is still named Axial_Stern_FixedSlotLips; that
    // name is not evidence that any of its 18 primitives belongs to a gun.
    if (node.userData.staticJoint !== true) continue
    if (node.name.startsWith('Hatch_')) return undefined
    const group = classifyWeaponJoint(node.name)
    if (group) return group
  }
  return undefined
}

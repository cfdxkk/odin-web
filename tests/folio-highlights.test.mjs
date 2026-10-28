import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { folioWeaponGroup } from '../app/lib/folio-highlights.ts'

function assetTree(file) {
  const bytes = readFileSync(
    new URL(`../public/models/${file}`, import.meta.url),
  )
  const gltf = JSON.parse(
    bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString(),
  )
  const nodes = gltf.nodes.map((node) => ({
    name: node.name,
    userData: node.extras || {},
    parent: null,
  }))
  gltf.nodes.forEach((node, index) =>
    (node.children || []).forEach((child) => {
      nodes[child].parent = nodes[index]
    }),
  )
  return {
    gltf,
    nodes,
    byName: (name) => nodes.find((node) => node.name === name),
  }
}

for (const file of ['odin.glb', 'odin-lite.glb']) {
  test(`${file}: merged hull primitives cannot inherit a weapon-like datablock name`, () => {
    const { gltf, nodes, byName } = assetTree(file)
    const hull = byName('Odin_Asset_Geometry')
    const hullIndex = nodes.indexOf(hull)
    const mesh = gltf.meshes[gltf.nodes[hullIndex].mesh]
    assert.ok(
      mesh.primitives.length >= 18,
      'Test the multi-material merged hull',
    )
    mesh.primitives.forEach((_, index) => {
      const primitive = {
        name: `${mesh.name}_${index}`,
        userData: {},
        parent: hull,
      }
      assert.equal(
        folioWeaponGroup(primitive),
        undefined,
        `${primitive.name} stays neutral`,
      )
    })
  })

  test(`${file}: all eleven secondary mounts retain their real rig ownership`, () => {
    const { byName } = assetTree(file)
    const names = ['Axial_Bow_Mount', 'Axial_Stern_Mount', 'Axial_Keel_Mount']
    for (let index = 1; index <= 4; index++)
      for (const side of ['Port', 'Starboard'])
        names.push(`SideBattery_${index}_${side}`)
    for (const name of names) {
      const parent = byName(name)
      assert.ok(parent, `${name} exists`)
      assert.equal(
        folioWeaponGroup({ name: 'anonymous_primitive', userData: {}, parent }),
        'single',
        name,
      )
    }
    for (const [name, expected] of [
      ['Main_Dorsal_Barrels', 'main'],
      ['Defense_01_Elevation', 'defense'],
      ['PDC_Port_Gimbal', 'quad'],
      ['Hatch_Dorsal_Port', undefined],
    ]) {
      const parent = byName(name)
      assert.ok(parent, `${name} exists`)
      assert.equal(
        folioWeaponGroup({ name: 'anonymous_primitive', userData: {}, parent }),
        expected,
        name,
      )
    }
  })
}

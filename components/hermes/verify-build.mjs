// Verify the actual packaged renderer inputs before patching, not a reference checkout.
import { readFileSync } from 'node:fs'
import { sourceHash } from '/opt/hermes/scripts/build/freshness.mjs'
const stamp = JSON.parse(readFileSync('/opt/hermes/install-stamp.json', 'utf8'))
if (stamp.commit !== '2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19' || stamp.dirty !== false) {
  throw new Error('Private Hermes patches require the pinned clean upstream source')
}
const expected = '1faeb5281c0b84c0d235e64dcebf8709a497e48dcb573181b46b2e959f27b0ca'
const receipt = JSON.parse(readFileSync('/opt/hermes/apps/desktop/dist-webapp/hermes-build.json', 'utf8'))
if (receipt.product !== 'webapp' || receipt.inputs.sourceHash !== expected ||
    sourceHash('/opt/hermes', 'webapp') !== expected) {
  throw new Error('Packaged Webapp source does not match the reviewed build inputs')
}

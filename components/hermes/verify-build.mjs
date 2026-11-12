// Verify the actual packaged renderer inputs before patching, not a reference checkout.
import { readFileSync } from 'node:fs'
import { sourceHash } from '/opt/hermes/scripts/build/freshness.mjs'
const stamp = JSON.parse(readFileSync('/opt/hermes/install-stamp.json', 'utf8'))
if (stamp.commit !== '3b421578588243f920886e6fe79a6faa87ea026e' || stamp.dirty !== false) {
  throw new Error('Private Hermes patches require the pinned clean upstream source')
}
const expected = 'd962149f7c279801f68eb629e8939592105e0d49ddb97d01a549b85748335717'
const receipt = JSON.parse(readFileSync('/opt/hermes/apps/desktop/dist-webapp/hermes-build.json', 'utf8'))
if (receipt.product !== 'webapp' || receipt.inputs.sourceHash !== expected ||
    sourceHash('/opt/hermes', 'webapp') !== expected) {
  throw new Error('Packaged Webapp source does not match the reviewed build inputs')
}

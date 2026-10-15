import { describe, expect, it } from 'vitest'
import { decide } from './decision'

const base = { distance_to_switch: 80, delay_score: 1 }
describe('AMRIN simulation decision engine', () => {
  it('clear_clear maintains Track A', () => expect(decide({ ...base }).action).toBe('MAINTAIN'))
  it('s3_on_A switches to Track B', () => expect(decide({ ...base, track_A_defect: 'S3' }).target_track).toBe('Track B'))
  it('s2_on_A_B_occupied maintains A with warning', () => { const result = decide({ ...base, track_A_defect: 'S2', track_B_occupied: true }); expect(result.action).toBe('MAINTAIN'); expect(result.action_level).toBe('WARNING') })
  it('both_s3 stops', () => expect(decide({ ...base, track_A_defect: 'S3', track_B_defect: 'S3' }).action).toBe('EMERGENCY_STOP'))
  it('too_close fails the distance rule', () => expect(decide({ ...base, distance_to_switch: 10 }).rules_checked[3].passed).toBe(false))
})

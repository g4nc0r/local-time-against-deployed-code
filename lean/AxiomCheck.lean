import LocalTime

-- Definitions and the abstract share lemma
#print axioms LocalTime.phi_eq_amounts
#print axioms LocalTime.share_add_eq_one
#print axioms LocalTime.min_ratio_le_one
#print axioms LocalTime.min_ratio_eq_one_iff

-- Theorem 2 (Share-Potential Identity) and the Free Locus, §The central law
#print axioms LocalTime.retained_eq_min_share_ratio
#print axioms LocalTime.retained_pos
#print axioms LocalTime.retained_le_one
#print axioms LocalTime.kerf_eq_max_log
#print axioms LocalTime.kerf_nonneg
#print axioms LocalTime.kerf_eq_zero_iff

-- The amplitude layer, §The amplitude layer
#print axioms LocalTime.cand0_form
#print axioms LocalTime.cand1_form
#print axioms LocalTime.cand_diff
#print axioms LocalTime.cand0_le_cand1
#print axioms LocalTime.cand1_le_cand0
#print axioms LocalTime.phi_old
#print axioms LocalTime.phi_new
#print axioms LocalTime.amplitude_up
#print axioms LocalTime.amplitude_dn
#print axioms LocalTime.ampDn_eq_cont_mul
#print axioms LocalTime.amplitude_corner_up
#print axioms LocalTime.amplitude_corner_dn
#print axioms LocalTime.gUp_eq
#print axioms LocalTime.gDn_eq
#print axioms LocalTime.hasDerivAt_gUp_zero
#print axioms LocalTime.hasDerivAt_gDn_zero

-- Down-Branch Monotonicity and its threshold
#print axioms LocalTime.ampDn_eq_Gdn
#print axioms LocalTime.hasDerivAt_Gdn
#print axioms LocalTime.GdnNum_corner
#print axioms LocalTime.GdnNum_sub_corner
#print axioms LocalTime.GdnNum_pos
#print axioms LocalTime.strictMonoOn_Gdn
#print axioms LocalTime.deriv_Gdn_corner_neg
#print axioms LocalTime.not_strictMonoOn_Gdn
#print axioms LocalTime.threshold_iff

-- Placement-Family Potentials, §The cost structure
#print axioms LocalTime.denom_pos
#print axioms LocalTime.phi_disp
#print axioms LocalTime.share0_eq_Qup
#print axioms LocalTime.share1_eq_Qdn
#print axioms LocalTime.shareRatio0_eq
#print axioms LocalTime.shareRatio1_eq
#print axioms LocalTime.kerf_eq_max_potential
#print axioms LocalTime.hasDerivAt_Cup
#print axioms LocalTime.Cup_deriv_pos
#print axioms LocalTime.strictMonoOn_Cup
#print axioms LocalTime.hasDerivAt_Cdn
#print axioms LocalTime.Cdn_deriv_neg
#print axioms LocalTime.strictAntiOn_Cdn
#print axioms LocalTime.round_trip_pos
#print axioms LocalTime.reduction_up
#print axioms LocalTime.reduction_dn

-- The corridor and the tangency constant, §The fixed-width floor
#print axioms LocalTime.tangency_upper
#print axioms LocalTime.tangency_lower
#print axioms LocalTime.tangency_upper_eq
#print axioms LocalTime.tangency_lower_eq
#print axioms LocalTime.corridor_gap_ge
#print axioms LocalTime.corridor_gap_eq_at_tangency
#print axioms LocalTime.corridor_gap_ge_inv
#print axioms LocalTime.corridor_ratio_era_bound
#print axioms LocalTime.hasDerivAt_Ufix
#print axioms LocalTime.hasDerivAt_Ffix
#print axioms LocalTime.hasDerivAt_Gfix
#print axioms LocalTime.antitoneOn_Ffix
#print axioms LocalTime.monotoneOn_Gfix
#print axioms LocalTime.fixed_impulse_inequality

-- The share corridor, §The width-uniform floor
#print axioms LocalTime.share_corridor_upper
#print axioms LocalTime.share_corridor_lower
#print axioms LocalTime.hasDerivAt_Ushare
#print axioms LocalTime.hasDerivAt_Fshare
#print axioms LocalTime.hasDerivAt_Gshare
#print axioms LocalTime.monotoneOn_Fshare
#print axioms LocalTime.antitoneOn_Gshare
#print axioms LocalTime.share_impulse_inequality

-- Achievability and Sharpness, §The fixed-width floor
#print axioms LocalTime.hasDerivAt_centredGap
#print axioms LocalTime.centredGap_deriv_nonneg
#print axioms LocalTime.monotoneOn_centredGap
#print axioms LocalTime.cCentred_ge_two
#print axioms LocalTime.cCentred_half
#print axioms LocalTime.hasDerivAt_cCentred
#print axioms LocalTime.cRefl_ge_two
#print axioms LocalTime.cRefl_half
#print axioms LocalTime.reflection_ratio_tendsto

-- The swap-mediated floor, §The swap-mediated floor
#print axioms LocalTime.swapCost_ge
#print axioms LocalTime.swapCost_fee_only
#print axioms LocalTime.fee_le_swapCost_fee_only
#print axioms LocalTime.dStar_root
#print axioms LocalTime.mint_leg_ge
#print axioms LocalTime.swap_impulse_inequality
#print axioms LocalTime.rSwap_antitone_in_x

-- The verification scheme in discrete monitoring, §The fixed-width floor
#print axioms LocalTime.Uquad_step
#print axioms LocalTime.discrete_verification
#print axioms LocalTime.discrete_floor
#print axioms LocalTime.discrete_floor_rate
#print axioms LocalTime.Ufix_eq_Uquad
#print axioms LocalTime.fixed_width_discrete_floor
#print axioms LocalTime.Ushare_eq_Uquad
#print axioms LocalTime.width_uniform_discrete_floor
#print axioms LocalTime.tangency_constant_rate
#print axioms LocalTime.swap_discrete_floor

-- Offset uniformity, §The equidistribution lemma
#print axioms LocalTime.monotone_lattice_sum
#print axioms LocalTime.bv_lattice_sum
#print axioms LocalTime.latticeA_le_latticeB
#print axioms LocalTime.latticeB_le_latticeA_succ
#print axioms LocalTime.offset_window_bound
#print axioms LocalTime.sup_dev_of_oscillation
#print axioms LocalTime.occupation_constant
#print axioms LocalTime.occupation_constant_value

-- The monitoring layer's normalisations, §Monitoring and §The forward map
#print axioms LocalTime.one_div_sqrt_eq_rpow
#print axioms LocalTime.delay_density_integral
#print axioms LocalTime.integral_Ioi_mul_exp_neg_half_sq
#print axioms LocalTime.integral_Ioi_mul_nden

-- Owen's T at infinity and the exact-reproduction core, §The forward map
#print axioms LocalTime.integrableOn_mul_exp_neg_mul_sq_div
#print axioms LocalTime.integral_Ioi_mul_exp_neg_mul_sq_div
#print axioms LocalTime.integral_Ioi_exp_neg_sq_mul
#print axioms LocalTime.owenKer_integrableOn
#print axioms LocalTime.owen_integrand_eq
#print axioms LocalTime.continuous_uncurry_owenKer
#print axioms LocalTime.owenKer_integrable_prod
#print axioms LocalTime.owen_reproduction
#print axioms LocalTime.surv_eq
#print axioms LocalTime.owenT_atTop

-- The retention collapse, §The retention collapse
#print axioms LocalTime.system_value_conserved
#print axioms LocalTime.token_conserved
#print axioms LocalTime.system_value_loss_eq_swap_cost

-- The jump surcharge, §The jump surcharge
#print axioms LocalTime.surcharge_telescopes
#print axioms LocalTime.surcharge_nonneg
#print axioms LocalTime.surcharge_pos
#print axioms LocalTime.surcharge_narrow_eq
#print axioms LocalTime.log_ratio_ge
#print axioms LocalTime.surcharge_narrow_ge

-- Leg comparison, §The two legs compared
#print axioms LocalTime.leg_ratio_isolated
#print axioms LocalTime.leg_ratio_swap
#print axioms LocalTime.leg_ratios_in_rho

-- The instrument's bracket and debiasing, §Identification and §Estimators
#print axioms LocalTime.exceedance_bracket
#print axioms LocalTime.jump_share_inversion
#print axioms LocalTime.jump_share_inversion_mono

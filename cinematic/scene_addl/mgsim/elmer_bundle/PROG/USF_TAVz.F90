! USF_TAVz.F90

FUNCTION BC_SIA_Tsicopolis (Model, nodenumber, Input) RESULT(SIAvx)
  USE types
  USE CoordinateSystems
  USE SolverUtils
  USE ElementDescription
  USE DefUtils
  IMPLICIT NONE
  TYPE(Model_t)              :: Model ! with this pointer, can access everything in a simulation
  TYPE(Solver_t), TARGET     :: Solver
  INTEGER                    :: nodenumber
  
  ! Input vector define
  REAL(dp)      :: Input(3) 

  ! locals
  REAL(dp) :: vc3, zsurf, zbed, z, H, Hglob, Ztilde
  REAL(dp) :: Tz, c0, c1, c2, c3, c4
  REAL(dp) :: yearinsec
  REAL(dp) :: A1si, A1, A2si, A2, Q1, Q2, Asi, A
  REAL(dp) :: alpha_deg, alpha_rad, n, m, C, Csi, rhoi, g
  REAL(dp) :: tau_fac
  REAL(dp) :: SIAvx_SI, SIAvx

  ! --- Unpack Input and derive geometry ---
  vc3   = Input(1)
  zsurf = Input(2)
  zbed  = Input(3)
  H = zsurf - zbed          ! local thickness
  z = vc3 - zbed           ! location above bed
  Ztilde = z/H

  ! --- Pull in constants from 'Constants' section of the .sif file ---
  c0 = ListGetConstReal( Model % Constants, 'c0', UnFoundFatal=.TRUE. )
  c1 = ListGetConstReal( Model % Constants, 'c1', UnFoundFatal=.TRUE. )
  c2 = ListGetConstReal( Model % Constants, 'c2', UnFoundFatal=.TRUE. )
  c3 = ListGetConstReal( Model % Constants, 'c3', UnFoundFatal=.TRUE. )
  c4 = ListGetConstReal( Model % Constants, 'c4', UnFoundFatal=.TRUE. )
  A1si = ListGetConstReal( Model % Constants, 'A1si', UnFoundFatal=.TRUE. )
  A2si = ListGetConstReal( Model % Constants, 'A2si', UnFoundFatal=.TRUE. )
  Q1 = ListGetConstReal( Model % Constants, 'Q1', UnFoundFatal=.TRUE. )
  Q2 = ListGetConstReal( Model % Constants, 'Q2', UnFoundFatal=.TRUE. )
  yearinsec = ListGetConstReal( Model % Constants, 'yearinsec', UnFoundFatal=.TRUE. )
  alpha_deg = ListGetConstReal( Model % Constants, 'alpha_deg', UnFoundFatal=.TRUE. )
  Hglob = ListGetConstReal( Model % Constants, 'Hglob', UnFoundFatal=.TRUE. )
  n = ListGetConstReal( Model % Constants, 'n', UnFoundFatal=.TRUE. )
  m = ListGetConstReal( Model % Constants, 'm', UnFoundFatal=.TRUE. )
  rhoi = ListGetConstReal( Model % Constants, 'rhoi', UnFoundFatal=.TRUE. )
  g = ListGetConstReal( Model % Constants, 'g', UnFoundFatal=.TRUE. )
  !gamma = ListGetConstReal( Model % Constants, 'gamma', UnFoundFatal=.TRUE. )
  Csi = ListGetConstReal( Model % Constants, 'Csi', UnFoundFatal=.TRUE. )
  !Asi_bed = ListGetConstReal( Model % Constants, 'Asi_bed', UnFoundFatal=.TRUE. ) !NOTE: be careful to ensure this is consistent with the bed temperature, temperature profiles for both user function and sif file

  ! --- Temperature profile (SICOPOLIS) ---
  IF (ABS(H) < 1.0e-12_dp) THEN
     Tz = c0 + c1*1 + c2*1**2 + c3*1**3 + c4*1**4
  ELSE
     Tz = c0 + c1*Ztilde + c2*Ztilde**2 + c3*Ztilde**3 + c4*Ztilde**4
  END IF

  ! --- Arrhenius A(T) (Pa^-n s^-1) with two-regime switch around -10C ---
  IF (Tz < -10.0_dp) THEN
     Asi = A1si * EXP( -Q1 / (8.314_dp * (273.15_dp + Tz)) )
  ELSE
     Asi = A2si * EXP( -Q2 / (8.314_dp * (273.15_dp + Tz)) )
  END IF

  ! --- SIA/sliding parameters ---
  alpha_rad = alpha_deg * (3.141592653589793_dp / 180.0_dp) ![rad]

  ! --- Final SIA + sliding boundary velocity (x-component) ---
  SIAvx_SI = 2.0_dp*Asi/(n+1.0_dp) * (rhoi*ABS(g)*ABS(alpha_rad))**n * (H**(n+1.0_dp) - (H-z)**(n+1.0_dp)) &
            + (rhoi*-g*H*ABS(alpha_rad)/Csi)**(1.0_dp/m)
  SIAvx = SIAvx_SI * yearinsec ! convert from [m/s] to [m/yr]

END FUNCTION BC_SIA_Tsicopolis

FUNCTION Tprof_sicopolis ( Model, nodenumber, Input) RESULT(Tz)
  USE types
  USE CoordinateSystems
  USE SolverUtils
  USE ElementDescription
  USE DefUtils
  IMPLICIT NONE
  TYPE(Model_t)::Model
  TYPE(Solver_t), TARGET::Solver
  INTEGER::nodenumber  
  REAL(KIND=dp)::Input(3)
  REAL(dp) :: vc3, zsurf, zbed, z, H, Ztilde
  REAL(KIND=dp)::Tz, c0, c1, c2, c3, c4

  ! --- Unpack Input and derive geometry ---
  vc3   = Input(1)
  zsurf = Input(2)
  zbed  = Input(3)
  H = zsurf - zbed          ! local thickness
  z = vc3 - zbed           ! location above bed
  Ztilde = z/H

  ! --- Pull in constants from 'Constants' section of the .sif file ---
  c0 = ListGetConstReal( Model % Constants, 'c0', UnFoundFatal=.TRUE. )
  c1 = ListGetConstReal( Model % Constants, 'c1', UnFoundFatal=.TRUE. )
  c2 = ListGetConstReal( Model % Constants, 'c2', UnFoundFatal=.TRUE. )
  c3 = ListGetConstReal( Model % Constants, 'c3', UnFoundFatal=.TRUE. )
  c4 = ListGetConstReal( Model % Constants, 'c4', UnFoundFatal=.TRUE. )

  ! --- Temperature profile (SICOPOLIS) ---
  IF (ABS(H) < 1.0e-12_dp) THEN
     Tz = c0 + c1*1 + c2*1**2 + c3*1**3 + c4*1**4
  ELSE
     Tz = c0 + c1*Ztilde + c2*Ztilde**2 + c3*Ztilde**3 + c4*Ztilde**4
  END IF

END FUNCTION Tprof_sicopolis


FUNCTION BC_SIA_Tlin (Model, nodenumber, Input) RESULT(SIAvx)
  USE types
  USE CoordinateSystems
  USE SolverUtils
  USE ElementDescription
  USE DefUtils
  IMPLICIT NONE
  TYPE(Model_t)              :: Model ! with this pointer, can access everything in a simulation
  TYPE(Solver_t), TARGET     :: Solver
  INTEGER                    :: nodenumber
  
  ! Input vector define
  REAL(dp)      :: Input(3) 

  ! locals
  REAL(dp) :: vc3, zsurf, zbed, z, H, Hglob
  REAL(dp) :: Tz, TtopC, TbotC
  REAL(dp) :: yearinsec
  REAL(dp) :: A1si, A1, A2si, A2, Q1, Q2, Asi, A, Asi_bed
  REAL(dp) :: alpha_deg, alpha_rad, n, m, C, Csi, rhoi, g, gamma
  REAL(dp) :: tau_fac
  REAL(dp) :: SIAvx_SI, SIAvx

  ! --- Unpack Input and derive geometry ---
  vc3   = Input(1)
  zsurf = Input(2)
  zbed  = Input(3)
  H = zsurf - zbed          ! local thickness
  z = vc3 - zbed           ! location above bed

  ! --- Pull in constants from 'Constants' section of the .sif file ---
  TtopC = ListGetConstReal( Model % Constants, 'TtopC', UnFoundFatal=.TRUE. )
  TbotC = ListGetConstReal( Model % Constants, 'TbotC', UnFoundFatal=.TRUE. )
  A1si = ListGetConstReal( Model % Constants, 'A1si', UnFoundFatal=.TRUE. )
  A2si = ListGetConstReal( Model % Constants, 'A2si', UnFoundFatal=.TRUE. )
  Q1 = ListGetConstReal( Model % Constants, 'Q1', UnFoundFatal=.TRUE. )
  Q2 = ListGetConstReal( Model % Constants, 'Q2', UnFoundFatal=.TRUE. )
  yearinsec = ListGetConstReal( Model % Constants, 'yearinsec', UnFoundFatal=.TRUE. )
  alpha_deg = ListGetConstReal( Model % Constants, 'alpha_deg', UnFoundFatal=.TRUE. )
  Hglob = ListGetConstReal( Model % Constants, 'Hglob', UnFoundFatal=.TRUE. )
  n = ListGetConstReal( Model % Constants, 'n', UnFoundFatal=.TRUE. )
  m = ListGetConstReal( Model % Constants, 'm', UnFoundFatal=.TRUE. )
  rhoi = ListGetConstReal( Model % Constants, 'rhoi', UnFoundFatal=.TRUE. )
  g = ListGetConstReal( Model % Constants, 'g', UnFoundFatal=.TRUE. )
  gamma = ListGetConstReal( Model % Constants, 'gamma', UnFoundFatal=.TRUE. )
  Csi = ListGetConstReal( Model % Constants, 'Csi', UnFoundFatal=.TRUE. )
  Asi_bed = ListGetConstReal( Model % Constants, 'Asi_bed', UnFoundFatal=.TRUE. ) !NOTE: be careful to ensure this is consistent with the bed temperature, temperature profiles for both user function and sif file

  ! --- Temperature profile (linear) ---
  IF (ABS(H) < 1.0e-12_dp) THEN
     Tz = TtopC
  ELSE
     Tz = TtopC + (TbotC - TtopC)*(zsurf - vc3)/((zsurf - zbed))
  END IF

  ! --- Arrhenius A(T) (Pa^-n s^-1) with two-regime switch around -10C ---
  IF (Tz < -10.0_dp) THEN
     Asi = A1si * EXP( -Q1 / (8.314_dp * (273.15_dp + Tz)) )
  ELSE
     Asi = A2si * EXP( -Q2 / (8.314_dp * (273.15_dp + Tz)) )
  END IF

  ! --- SIA/sliding parameters ---
  alpha_rad = alpha_deg * (3.141592653589793_dp / 180.0_dp) ![rad]

  ! --- Final SIA + sliding boundary velocity (x-component) ---
  SIAvx_SI = 2.0_dp*Asi/(n+1.0_dp) * (rhoi*ABS(g)*ABS(alpha_rad))**n * (H**(n+1.0_dp) - (H-z)**(n+1.0_dp)) &
            + (rhoi*-g*H*ABS(alpha_rad)/Csi)**(1.0_dp/m)
  SIAvx = SIAvx_SI * yearinsec ! convert from [m/s] to [m/yr]

END FUNCTION BC_SIA_Tlin


FUNCTION Tproflin ( Model, nodenumber, Input) RESULT(Tz)
  USE types
  USE CoordinateSystems
  USE SolverUtils
  USE ElementDescription
  USE DefUtils
  IMPLICIT NONE
  TYPE(Model_t)::Model
  TYPE(Solver_t), TARGET::Solver
  INTEGER::nodenumber  
  REAL(KIND=dp)::Input(3)
  REAL(dp) :: vc3, zsurf, zbed, z, H
  REAL(KIND=dp)::TtopC,TbotC,Tz

  ! --- Unpack Input and derive geometry ---
  vc3   = Input(1)
  zsurf = Input(2)
  zbed  = Input(3)
  H = zsurf - zbed          ! local thickness
  z = vc3 - zbed           ! location above bed

  ! --- Pull in constants from 'Constants' section of the .sif file ---
  TtopC = ListGetConstReal( Model % Constants, 'TtopC', UnFoundFatal=.TRUE. )
  TbotC = ListGetConstReal( Model % Constants, 'TbotC', UnFoundFatal=.TRUE. )

  ! --- Temperature profile (linear) --- NOTE: MAKE SURE THIS MATCHES THE TEMP PROFILE IN THE BCsia FUNCTION ABOVE
  IF (ABS(H) < 1.0e-12_dp) THEN
     Tz = TtopC
  ELSE
     Tz = TtopC + (TbotC - TtopC)*(zsurf - vc3)/((zsurf - zbed))
  END IF

END FUNCTION Tproflin




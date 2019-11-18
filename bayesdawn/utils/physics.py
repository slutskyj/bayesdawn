import numpy as np
import pyFDresponse as fd_resp
import Cosmology
import LISAConstants as LC
import lisabeta.lisa.ldctools as ldctools
import pyFDresponse as FD_Resp
from bayesdawn.gaps import gapgenerator


def compute_masses(mc, q):
    """

    Parameters
    ----------
    mc : float
        chirp mass (any unit)
    q : float
        mass ratio

    Returns
    -------
    m1 : float
        mass of object 1
    m2 : float
        mass of object 2

    """

    ma = (q / ((q + 1.) ** 2)) ** (-3.0 / 5.0)
    mb = ((q / ((q + 1.) ** 2)) ** (-6.0 / 5.0) - 4.0 * (q / ((q + 1.) ** 2)) ** (-1.0 / 5.0)) ** 0.5

    m1 = 0.5 * mc * (ma + mb)
    m2 = 0.5 * mc * (ma - mb)

    return m1, m2


def like_to_waveform(par):
    """
    Convert likelihood parameters into waveform-compatible parameters
    Parameters
    ----------
    par : array_like
        parameter vector for sampling the posterior:
        Mc, q, tc, chi1, chi2, np.log10(DL), np.cos(incl), np.sin(bet), lam, psi, phi0

    Returns
    -------
    params : array_like
       parameter vector for LISABeta waveform: m1, m2, chi1, chi2, del_t, dist, incl, phi0, lam, bet, psi

    """

    # Explicit the vector of paramters
    mc, q, tc, chi1, chi2, logdl, ci, sb, lam, psi, phi0 = par

    # Convert chirp mass into individual masses
    m1, m2 = compute_masses(mc, q)

    # Convert base-10 logarithmic luminosity distance into lum. dist. in Mega parsecs
    dl = 10.0 ** logdl

    # Convert inclination
    incl = np.arccos(ci)
    # Convert Source latitude in SSB-frame
    bet = np.arcsin(sb)

    params = np.array([m1, m2, chi1, chi2, tc, dl, incl, phi0, lam, bet, psi])

    return params


def waveform_to_like(params):
    """
    Convert lisabeta waveform parameters to sampled parameters
    Parameters
    ----------
    params

    Returns
    -------

    """

    m1, m2, chi1, chi2, tc, dl, incl, phi0, lam, bet, psi = params

    mc = fd_resp.funcMchirpofm1m2(m1, m2)
    q = m1 / m2

    # transforming into sampling parameters
    par = np.array([mc, q, tc, chi1, chi2, np.log10(dl), np.cos(incl), np.sin(bet), lam, psi, phi0])

    return par


def like_to_waveform_intr(par_intr):
    """
    Convert likelihood parameters into waveform-compatible parameters
    Parameters
    ----------
    par : array_like
        parameter vector for sampling the posterior:
        Mc, q, tc, chi1, chi2, np.log10(DL), np.cos(incl), np.sin(bet), lam, psi, phi0

    Returns
    -------
    params : array_like
       parameter vector for LISABeta waveform: m1, m2, chi1, chi2, del_t, dist, incl, phi0, lam, bet, psi

    """

    # Explicit the vector of paramters
    mc, q, tc, chi1, chi2, sb, lam = par_intr

    # Convert chirp mass into individual masses
    m1, m2 = compute_masses(mc, q)

    # Convert Source latitude in SSB-frame
    bet = np.arcsin(sb)

    params = np.array([m1, m2, chi1, chi2, tc, lam, bet])

    return params


def get_params(p_gw, sampling=False):
    """
    returns array of parameters from hdf5 structure
    Parameters
    ----------
    p_gw : ParsUnits instance
        waveform parameter object

    Returns
    -------

    """
    # print (pGW.get('Mass1')*1.e-6, pGW.get('Mass2')*1.e-6)
    m1 = p_gw.get('Mass1') ### Assume masses redshifted
    m2 = p_gw.get('Mass2')
    tc = p_gw.get('CoalescenceTime')
    chi1 = p_gw.get('Spin1') * np.cos(p_gw.get('PolarAngleOfSpin1'))
    chi2 = p_gw.get('Spin2') * np.cos(p_gw.get('PolarAngleOfSpin2'))
    phi0 = p_gw.get('PhaseAtCoalescence')
    z = p_gw.get("Redshift")
    DL = Cosmology.DL(z, w=0)[0]
    dist = DL * 1.e6 * LC.pc
    print ("DL = ", DL*1.e-3, "Gpc")
    print ("Compare DL:", p_gw.getConvert('Distance', LC.convDistance, 'mpc'))

    bet, lam, incl, psi = ldctools.GetSkyAndOrientation(p_gw)

    if not sampling:
        return m1, m2, tc, chi1, chi2, dist, incl, bet, lam, psi, phi0, DL
    else:
        # Get parameters as an array from the hdf5 structure (table)
        Mc = FD_Resp.funcMchirpofm1m2(m1, m2)
        q = m1 / m2
        # transforming into sampling parameters
        ps_sampl = np.array([Mc, q, tc, chi1, chi2, np.log10(DL), np.cos(incl), np.sin(bet), lam, psi, phi0])

        return ps_sampl


def compute_frequency_vs_time(t, m_chirp, t_merger):
    """

    Compute frequency as a function of time at 1 PN order

    Parameters
    ----------
    t : array_like
        time vector [seconds]
    m_chirp : scalar float
        chirp mass [solar mass]
    t_merger : scalar float
        time to merger [seconds]

    Returns
    -------
    f_dot : scalar float
        source frequency derivative [Hz/s]


    """

    # Convert merger time from seconds to years
    t_merger_years = t_merger / LC.year

    # Compute starting frequency (source frequency at t=0 [Hz]) as a function of time to merger
    f_start = FD_Resp.funcNewtonianfoft(m_chirp, t_merger_years)

    # Convert chirp mass in kg
    # m_chirp_kg = m_chirp*LC.MsunKG

    # Compute involved constant
    # k = 96/5.*np.pi**(8/3.)*(LC.G*m_chirp_kg/LC.c**3)**(5/3.)

    # ft = (f_start**(-8/3) - 8/3 * k * t)**(-3/8)
    ft = f_start * (1 - t / t_merger) ** (-3/8)

    return ft


def find_distorted_interval(mask, p_sampl, t0, del_t, margin=0):

    m_chirp = p_sampl[0]
    t_merger = p_sampl[2]
    nd, nf = gapgenerator.find_ends(mask)
    t1 = del_t * nd[0]
    t2 = del_t * nf[-1]

    f1 = compute_frequency_vs_time(t1, m_chirp, t_merger - t0)
    f2 = compute_frequency_vs_time(t2, m_chirp, t_merger - t0)

    return f1 * (1 - margin), f2 * (1 + margin)


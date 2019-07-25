#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 22 15:59:04 2019

Class to set up a simple Metropolis Hasting sampler for the PSD parameters

@author: qbaghi
"""

import numpy as np
from ..psd import psdspline2
from . import mhmcmc
from scipy import interpolate


class PSDSampler(psdspline2.PSD_spline, mhmcmc.MHSampler):
    """
    
    ** ** 
    TODO : Add z_fft as a permanent attribute for this class!!!
    Will be much better
    ** ** 
    
    
    """    
    
    def __init__(self, Neff, fs, J=30, D=3, fmin=None, fmax=None):

        psdspline2.PSD_spline.__init__(self, Neff, fs, J=J, D=D, fmin=fmin, fmax=fmax)
        
        # Periodogram of the residuals is an attribute
        self.I = []
        # Initialize the sampler
        mhmcmc.MHSampler.__init__(self, J+1, self.psd_posterior)

    def set_periodogram(self, z_fft, K2=None):
        """
        Assign a value to the periodogram attribute

        Parameters
        ----------
        z_fft : array_like
            vector of residal DFT     
        K2 : scalar float
            periodogram normalization. Should always be 
            sum(W**2) where W is the window function applied in the time domain.
            If K2 is None, the length N of the data is taken.
        
        """
        if type(z_fft) == np.ndarray :
            self.I = self.periodogram(z_fft, K2 = K2)
        elif type(z_fft) == list:
            self.I = [self.periodogram(zf, K2 = K2) for zf in z_fft]

    def psd_likelihood(self, x):
        """

        Compute log-likelihood for the PSD update

        Parameters
        ----------
        x: array_like
            vector of log-PSD values at specific frequencies
            
        Returns
        -------
        ll : scalar float
            value of the log-likelihood

        """

        logSfunc = interpolate.interp1d(self.logfc, x, kind='cubic', fill_value="extrapolate")
        
        # If only one segment of data is analyzed
        if type(self.I) == np.ndarray:
            logS = logSfunc(self.logf[self.N])
            I_weighted = self.I[1:self.n+1] * np.exp( - logS )
            ll = np.real( -0.5*np.sum( logS + I_weighted ) )
            
        # If several segments of different lengths are considered:
        elif type(self.I) == list:
            Nsegs = list(self.logf.keys())
            Ls = len(Nsegs)
            logS_list = [logSfunc(self.logf[self.NI]) for NI in Nsegs]
            
            I_weighted_list = [self.I[j][1:np.int((Nsegs[j]-1)/2)+1] * np.exp( - logS_list[j] ) \
                          for j in range(Ls)]
            
            ll = sum([np.real( -0.5*np.sum( logS_list[j] + I_weighted_list[j] ) ) for j in range(Ls)])

        return ll

    def psd_prior(self, x):
        """

        Compute the log-prior probability density for the PSD parameters

        """

        return -0.5 * np.sum((x - self.logSc)**2 / (2*self.varlogSc))

    def psd_posterior(self, x_psd):
        """
        Compute the log-posterior probability density for the PSD parameters

        """

        return self.psd_likelihood(x_psd) + self.psd_prior(x_psd)

    def update_psd_func(self, logSc, kind='cubic'):
        """

        Update the interpolating function of the PSD with new control
        values logS

        """
        # Update PSD interpolation function
        self.logPSD_fn = interpolate.interp1d(self.logfc, logSc, kind=kind, fill_value="extrapolate")
        self.S = self.calculate(self.N)

    def sample_psd(self, nit, verbose=True, cov_update=1000):
        """
        Update PSD parameters 
        
        Parameters
        ----------
        noise_params : array_like
            noise parameters
        residual_fft : array_like of size N
            discrete Fourier transform of the model residuals
        wd : array_like of size N
            apodization window (optional)
            
        Returns
        -------
        noise_params_new : array_like
            updated PSD parameters
            
            
        """

        # Update likelihood
        self.logp_tilde = self.psd_posterior
        # update PSD parameters by MH steps
        psd_samples, logpvalues = self.run_mcmc(np.copy(self.logSc), self.varlogSc/(self.J+1), nit,
                                                verbose=verbose,
                                                cov_update=cov_update)

        return psd_samples, logpvalues



#    def sample_psd(self,residual_fft,nit,verbose = True, cov_update = 1000,K2 = None):
#        """
#        Update PSD parameters 
#        
#        Parameters
#        ----------
#        noise_params : array_like
#            noise parameters
#        residual_fft : array_like of size N
#            discrete Fourier transform of the model residuals
#        wd : array_like of size N
#            apodization window (optional)
#            
#        Returns
#        -------
#        noise_params_new : array_like
#            updated PSD parameters
#            
#            
#        """
#    
#        # Update the periodogram
#        self.set_periodogram(residual_fft, K2 = K2)
#        # Update likelihood
#        self.logp_tilde = self.psd_posterior
#        # update PSD parameters by MH steps
#        psd_samples,logpvalues = self.run_mcmc(np.copy(self.logSc),nit,
#                                               verbose = verbose,
#                                               cov_update = cov_update)
#
#        
#        return psd_samples,logpvalues
      
        
#    def sample_psd(self,noise_params,residual_fft,nit):
#        """
#        Update PSD parameters 
#        
#        Parameters
#        ----------
#        noise_params : array_like
#            noise parameters
#        residual_fft : array_like
#            discrete Fourier transform of the model residuals
#            
#        Returns
#        -------
#        noise_params_new : array_like
#            updated PSD parameters
#            
#            
#        """
#    
#        # Update the periodogram
#        self.set_periodogram(residual_fft)
#        # Update likelihood
#        self.logp_tilde = self.psd_posterior
#        # update PSD parameters by MH steps
#        psd_samples,logpvalues = self.run_mcmc(noise_params,nit,verbose = True)
#        # Last PSD value
#        noise_params_new = psd_samples[nit-1,:]
#        # Update PSD function and Fourier spectrum
#        self.update_psd_func(noise_params_new)
#        
#        return noise_params_new
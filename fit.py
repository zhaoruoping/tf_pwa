#!/usr/bin/env python3

import json
import time
from pprint import pprint

# avoid using Xwindow
import matplotlib

matplotlib.use("agg")

import tensorflow as tf

# examples of custom particle model
from tf_pwa.amp import simple_resonance
from tf_pwa.config_loader import ConfigLoader, MultiConfig
from tf_pwa.experimental import extra_amp, extra_data
from tf_pwa.utils import error_print


@simple_resonance("New", params=["alpha", "beta"])
def New_Particle(m, alpha, beta=0):
    """example Particle model define, can be used in config.yml as `model: New`"""
    zeros = tf.zeros_like(m)
    r = -tf.complex(alpha, beta) * tf.complex(m, zeros)
    return tf.exp(r)


def json_print(dic):
    """print parameters as json"""
    s = json.dumps(dic, indent=2)
    print(s, flush=True)


def load_config(config_file="config.yml", total_same=False):
    config_files = config_file.split(",")
    if len(config_files) == 1:
        return ConfigLoader(config_files[0])
    return MultiConfig(config_files, total_same=total_same)


def fit(config, init_params="", method="BFGS", loop=1):
    """
    simple fit script
    """
    # load config.yml
    # config = ConfigLoader(config_file)

    # load data
    all_data = config.get_all_data()

    fit_results = []
    for i in range(loop):
        # set initial parameters if have
        if config.set_params(init_params):
            print("using {}".format(init_params))
        else:
            print("\nusing RANDOM parameters", flush=True)
        # try to fit
        try:
            fit_result = config.fit(batch=65000, method=method)
        except KeyboardInterrupt:
            config.save_params("break_params.json")
            raise
        except Exception as e:
            print(e)
            config.save_params("break_params.json")
            raise
        fit_results.append(fit_result)
        # reset parameters
        try:
            config.reinit_params()
        except Exception as e:
            print(e)

    fit_result = fit_results.pop()
    for i in fit_results:
        if i.success:
            if not fit_result.success or fit_result.min_nll > i.min_nll:
                fit_result = i

    config.set_params(fit_result.params)
    json_print(fit_result.params)
    fit_result.save_as("final_params.json")

    # calculate parameters error
    fit_error = config.get_params_error(fit_result, batch=13000)
    fit_result.set_error(fit_error)
    fit_result.save_as("final_params.json")
    pprint(fit_error)

    print("\n########## fit results:")
    print("Fit status: ", fit_result.success)
    print("Minimal -lnL = ", fit_result.min_nll)
    for k, v in config.get_params().items():
        print(k, error_print(v, fit_error.get(k, None)))

    return fit_result


def write_some_results(config, fit_result):
    # plot partial wave distribution
    config.plot_partial_wave(fit_result, plot_pull=True)

    # calculate fit fractions
    phsp_noeff = config.get_phsp_noeff()
    fit_frac, err_frac = config.cal_fitfractions({}, phsp_noeff)

    print("########## fit fractions")
    fit_frac_string = ""
    for i in fit_frac:
        if isinstance(i, tuple):
            name = "{}x{}".format(*i)
        else:
            name = i
        fit_frac_string += "{} {}\n".format(
            name, error_print(fit_frac[i], err_frac.get(i, None))
        )
    print(fit_frac_string)
    # from frac_table import frac_table
    # frac_table(fit_frac_string)
    # chi2, ndf = config.cal_chi2(mass=["R_BC", "R_CD"], bins=[[2,2]]*4)


def write_some_results_combine(config, fit_result):

    from tf_pwa.applications import fit_fractions

    for i, c in enumerate(config.configs):
        c.plot_partial_wave(fit_result, prefix="figure/s{}_".format(i))

    for it, config_i in enumerate(config.configs):
        print("########## fit fractions {}:".format(it))
        mcdata = config_i.get_phsp_noeff()
        fit_frac, err_frac = fit_fractions(
            config_i.get_amplitude(),
            mcdata,
            config.inv_he,
            fit_result.params,
        )
        fit_frac_string = ""
        for i in fit_frac:
            if isinstance(i, tuple):
                name = "{}x{}".format(*i)  # interference term
            else:
                name = i  # fit fraction
            fit_frac_string += "{} {}\n".format(
                name, error_print(fit_frac[i], err_frac.get(i, None))
            )
        print(fit_frac_string)
    # from frac_table import frac_table
    # frac_table(fit_frac_string)


def write_run_point():
    """ write time as a point of fit start"""
    with open(".run_start", "w") as f:
        localtime = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
        )
        f.write(localtime)


def main():
    """entry point of fit. add some arguments in commond line"""
    import argparse

    parser = argparse.ArgumentParser(description="simple fit scripts")
    parser.add_argument(
        "--no-GPU", action="store_false", default=True, dest="has_gpu"
    )
    parser.add_argument("-c", "--config", default="config.yml", dest="config")
    parser.add_argument(
        "-i", "--init_params", default="init_params.json", dest="init"
    )
    parser.add_argument("-m", "--method", default="BFGS", dest="method")
    parser.add_argument("-l", "--loop", type=int, default=1, dest="loop")
    parser.add_argument(
        "--total-same", action="store_true", default=False, dest="total_same"
    )
    results = parser.parse_args()
    if results.has_gpu:
        devices = "/device:GPU:0"
    else:
        devices = "/device:CPU:0"
    with tf.device(devices):
        config = load_config(results.config, results.total_same)
        fit_result = fit(config, results.init, results.method, results.loop)
        if isinstance(config, ConfigLoader):
            write_some_results(config, fit_result)
        else:
            write_some_results_combine(config, fit_result)


if __name__ == "__main__":
    write_run_point()
    main()

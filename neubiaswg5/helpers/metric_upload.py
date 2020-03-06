import logging
import os
import warnings
from collections import defaultdict

from cytomine import CytomineJob
from cytomine.models import Project

from neubiaswg5 import CLASS_TRETRC, CLASS_OBJTRK
from neubiaswg5.helpers.cytomine_metrics import MetricCollection, get_metric_result_collection, get_metric_result
from neubiaswg5.metrics import computemetrics_batch


def get_compute_mode(problemclass):
    """Check which type of files should be used for computing the metrics for the given problemclass.

    Parameters
    ----------
    problemclass: str
        The problem class

    Returns
    -------
    use_mask: bool
        True if should use a mask
    use_attached: bool
        True if should use an attached file
    """
    if problemclass == CLASS_OBJTRK:  # use both files
        return True, True
    elif problemclass == CLASS_TRETRC:
        return False, True
    else:  # only mask by default
        return True, False


def check_file(filepath, message):
    if not os.path.isfile(filepath):
        raise ValueError("File '{}' missing: {}".format(filepath, message))
    return filepath


def upload_metrics(problemclass, nj, inputs, gt_path, out_path, tmp_path, metric_params=None, **kwargs):
    """Upload each sample will get a value for each metrics of the given problemclass
    Parameters
    ----------
    problemclass: str
        Problem class
    nj: CytomineJob|BiaflowsJob
        A CytomineJob or BiaflowsJob instance.
    inputs: iterable
        A list of input data for which the metrics must be computed
    gt_path: str
        Absolute path to the ground truth data
    out_path: str
        Absolute path to the output data
    tmp_path: str
        Absolute path to a temporary folder
    metric_params: dict
        Additional parameters for metric computation (forwarded to computemetrics or computemetrics_batch directly)
    """
    if not nj.flags["do_compute_metrics"]:
        return
    if nj.flags["tiling"]:
        print("Metric computation not supported when tiling is enabled. Skip!")
        return
    if len(inputs) == 0:
        print("Skipping metric computation because there is no images to process.")
        return
    if metric_params is None:
        metric_params = dict()

    use_mask, use_attached = get_compute_mode(problemclass)

    # list files to be used for computing metrics
    outfiles, reffiles = list(), list()
    for i, in_image in enumerate(inputs):
        out, gt = [], []
        if use_mask:
            out.append(check_file(os.path.join(out_path, in_image.filename), "an output mask is expected for input image '{}'".format(in_image.filename)))
            gt.append(check_file(os.path.join(gt_path, in_image.filename), "an ground truth mask is expected for input image '{}'".format(in_image.filename)))
        if use_attached:
            if len(in_image.attached) == 0:
                raise ValueError("No attached file found although attached files were selected for computing metrics.")
            out_filename = in_image.filename_no_extension + "." + in_image.attached[0].extension
            out.append(check_file(os.path.join(out_path, out_filename), "an output file is expected for input image '{}'".format(in_image.filename)))
            gt.append(check_file(os.path.join(gt_path, in_image.attached[0].filename), "an ground truth file is expected for input image '{}'".format(in_image.filename)))

        if len(out) > 1:  # use both mask and attached
            outfiles.append(out)
            reffiles.append(gt)
        else:  # use only one type of file
            outfiles.append(out[0])
            reffiles.append(gt[0])

    results, params = computemetrics_batch(outfiles, reffiles, problemclass, tmp_path, **metric_params)

    print("Metrics:")
    for i, image in enumerate(inputs):
        print("> {}: [{}]".format(
            image.filename,
            ", ".join(["{}:{}".format(metric_name, metric_values[i]) for metric_name, metric_values in results.items()])
        ))

    if not nj.flags["do_upload_metrics"]:
        return

    # effectively upload metrics
    project = Project().fetch(nj.project.id)
    metrics = MetricCollection().fetch_with_filter("discipline", project.discipline)

    metric_collection = get_metric_result_collection(inputs[0].object)
    per_input_metrics = defaultdict(dict)
    for metric_name, values in results.items():
        # check if metric is supposed to be computed for this problem class
        metric = metrics.find_by_attribute("shortName", metric_name)
        if metric is None:
            print("Skip metric '{}' because not listed as a metric of the problem class '{}'.".format(metric_name, problemclass))
            continue
        # create metric results
        for i, in_image in enumerate(inputs):
            image = in_image.object
            metric_result = get_metric_result(image, id_metric=metric.id, id_job=nj.job.id, value=values[i])
            metric_collection.append(metric_result)

            # for logging
            image_dict = per_input_metrics.get(image.id, {})
            image_dict[metric.shortName] = image_dict.get(metric.shortName, []) + [values[i]]
            per_input_metrics[image.id] = image_dict

    metric_collection.save()

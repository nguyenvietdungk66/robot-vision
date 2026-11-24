from nodes.Filter.algorithms import gaussian_blur, bilateral_filter, nlm

FILTERS = {
    "Gaussian Blur": gaussian_blur.apply,
    "Bilateral Filter": bilateral_filter.apply,
    "Non-Local Means": nlm.apply,
}

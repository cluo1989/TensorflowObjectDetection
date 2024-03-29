# coding: utf-8
import tensorflow as tf


def augment(image, input_shape, data_format, output_shape, zoom_size=None,
            crop_method=None, flip_prob=None, fill_mode='BILINEAR', keep_aspect_ratios=False,
            constant_values=0., color_jitter_prob=None, rotate=None, ground_truth=None, pad_truth_to=None):

    """
    :param image: HWC or CHW
    :param input_shape: [h, w]
    :param data_format: 'channels_first', 'channels_last'
    :param output_shape: [h, w]
    :param zoom_size: [h, w]
    :param crop_method: 'random', 'center'
    :param flip_prob: [flip_top_down_prob, flip_left_right_prob]
    :param fill_mode: 'CONSTANT', 'NEAREST_NEIGHBOR', 'BILINEAR', 'BICUBIC'
    :param keep_aspect_ratios: True, False
    :param constant_values:
    :param color_jitter_prob: prob of color_jitter
    :param rotate: [prob, min_angle, max_angle]
    :param ground_truth: [ymin, ymax, xmin, xmax, classid]
    :param pad_truth_to: pad ground_truth to size [pad_truth_to, 5] with -1
    :return image: output_shape
    :return ground_truth: [pad_truth_to, 5] [ycenter, xcenter, h, w, class_id]
    """
    # ------------------- do vilidation ---------------------
    if data_format not in ['channels_first', 'channels_last']:
        raise Exception("data_format must in ['channels_first', 'channels_last']!")

    if fill_mode not in ['CONSTANT', 'NEAREST_NEIGHBOR', 'BILINEAR', 'BICUBIC']:
        raise Exception("fill_mode must in ['CONSTANT', 'NEAREST_NEIGHBOR', 'BILINEAR', 'BICUBIC']!")

    if fill_mode == 'CONSTANT' and zoom_size is not None:
        raise Exception("if fill_mode is 'CONSTANT', zoom_size can't be None!")

    if zoom_size is not None:
        if keep_aspect_ratios:
            if constant_values is None:
                raise Exception('please provide constant_values!')

        if not zoom_size[0] >= output_shape[0] and zoom_size[1] >= output_shape[1]:
            raise Exception("output_shape can't greater that zoom_size!")

        if crop_method not in ['random', 'center']:
            raise Exception("crop_method must in ['random', 'center']!")

        if fill_mode is 'CONSTANT' and constant_values is None:
            raise Exception("please provide constant_values!")

    if color_jitter_prob is not None:
        if not 0. <= color_jitter_prob <= 1.:
            raise Exception("color_jitter_prob can't less that 0.0, and can't grater that 1.0")

    if flip_prob is not None:
        if not 0. <= flip_prob[0] <= 1. and 0. <= flip_prob[1] <= 1.:
            raise Exception("flip_prob can't less than 0.0, and can't grater than 1.0")

    if rotate is not None:
        if len(rotate) != 3:
            raise Exception('please provide "rotate" parameter as [rotate_prob, min_angle, max_angle]!')

        if not 0. <= rotate[0] <= 1.:
            raise Exception("rotate prob can't less that 0.0, and can't grater that 1.0")

        if ground_truth is not None:
            if not -5. <= rotate[1] <= 5. and -5. <= rotate[2] <= 5.:
                raise Exception('rotate range must be -5 to 5, otherwise coordinate mapping become imprecise!')

        if not rotate[1] <= rotate[2]:
            raise Exception("rotate[1] can't  grater than rotate[2]")

    # ------------------- do augmentation ---------------------
    # in order to keep aspect ratio, resize longside
    # and padding short-side with CONSTANT to get specific size, i.e (zoom or output_shape)
    if fill_mode == 'CONSTANT':
        keep_aspect_ratios = True

    fill_mode_project = {
        'NEAREST_NEIGHBOR': tf.image.ResizeMethod.NEAREST_NEIGHBOR,
        'BILINEAR': tf.image.ResizeMethod.BILINEAR,
        'BICUBIC': tf.image.ResizeMethod.BICUBIC
    }

    # [ymin, ymax, xmin, xmax, id] -> [ycenter, xcenter, h, w, id]
    if ground_truth is not None:
        ymin = tf.reshape(ground_truth[:, 0], [-1, 1])
        ymax = tf.reshape(ground_truth[:, 1], [-1, 1])
        xmin = tf.reshape(ground_truth[:, 2], [-1, 1])
        xmax = tf.reshape(ground_truth[:, 3], [-1, 1])
        class_id = tf.reshape(ground_truth[:, 4], [-1, 1])
        yy = (ymin + ymax) / 2.
        xx = (xmin + xmax) / 2.
        hh = ymax - ymin
        ww = xmax -xmin

    # copy 
    image_copy = image

    # CHW -> HWC
    if data_format == 'channels_first':
        image = tf.transpose(image, [1, 2, 0])

    # get input image shape and output size
    input_h, input_w, input_c = input_shape[0], input_shape[1], input_shape[2]
    output_h, output_w = output_shape

    # get zoom size
    if zoom_size is not None:
        zoom_or_output_h, zoom_or_output_w = zoom_size
    else:
        zoom_or_output_h, zoom_or_output_w = output_shape

    # resize ---------------------------------------
    # keep aspect
    # won't cause distortion
    if keep_aspect_ratios:
        if fill_mode in ['NEAREST_NEIGHBOR', 'BILINEAR', 'BICUBIC']:
            # ratio of long-side resize
            zoom_ratio = tf.cond(
                tf.less(zoom_or_output_h / input_h, zoom_or_output_w / input_w),
                lambda: tf.cast(zoom_or_output_h / input_h, tf.float32),
                lambda: tf.cast(zoom_or_output_w / input_w, tf.float32)
            )

            # new height and width
            resize_h, resize_w = tf.cond(
                tf.less(zoom_or_output_h / input_h, zoom_or_output_w / input_w),
                lambda: (zoom_or_output_h, tf.cast(tf.cast(input_w, tf.float32) * zoom_ratio, tf.int32)),
                lambda: (tf.cast(tf.cast(input_h, tf.float32)*zoom_ratio, tf.int32), zoom_or_output_w)
            )

            # resize image
            image = tf.image.resize_images(
                image, [resize_h, resize_w], fill_mode_project[fill_mode],
                align_corners=True,
            )

            # resize ground truth
            if ground_truth is not None:
                ymin, ymax = ymin * zoom_ratio, ymax * zoom_ratio
                xmin, xmax = xmin * zoom_ratio, xmax * zoom_ratio

            # padding short-side
            # at bottom or right
            image = tf.pad(
                image, [[0, zoom_or_output_h-resize_h], [0, zoom_or_output_w-resize_w], [0, 0]],
                mode='CONSTANT', constant_values=constant_values
            )
        else:
            # directly pad along bottom and right
            # to get specific size i.e (zoom or output_shape)
            image = tf.pad(
                image, [[0, zoom_or_output_h-input_h], [0, zoom_or_output_w-input_w], [0, 0]],
                mode='CONSTANT', constant_values=constant_values
            )
    # no keep aspect
    # will cause distortion
    else:
        # resize to zoom or output shape
        # without padding
        image = tf.image.resize_images(
            image, [zoom_or_output_h, zoom_or_output_w], fill_mode_project[fill_mode],
            align_corners=True, preserve_aspect_ratio=False
        )

        # resize ground truth coords
        if ground_truth is not None:
            zoom_ratio_y = tf.cast(zoom_or_output_h / input_h, tf.float32)
            zoom_ratio_x = tf.cast(zoom_or_output_w / input_w, tf.float32)
            ymin, ymax = ymin * zoom_ratio_y, ymax * zoom_ratio_y
            xmin, xmax = xmin * zoom_ratio_x, xmax * zoom_ratio_x
    # ---------------------------------------------

    # crop using zoom sized image，size: [output_h, output_w]
    # no zoom no crop
    if zoom_size is not None:
        # random crop, top-left
        if crop_method == 'random':
            random_h = zoom_or_output_h - output_h
            random_w = zoom_or_output_w - output_w
            crop_h = tf.random_uniform([], 0, random_h, tf.int32)
            crop_w = tf.random_uniform([], 0, random_w, tf.int32)
        # center crop
        else:
            crop_h = (zoom_or_output_h - output_h) // 2
            crop_w = (zoom_or_output_w - output_w) // 2

        # do image cropping
        # tf.slice(image, start, size)
        image = tf.slice(
            image, [crop_h, crop_w, 0], [output_h, output_w, input_c]
        )

        # crop ground truth coords
        if ground_truth is not None:
            ymin = tf.maximum(ymin - tf.cast(crop_h, tf.float32), 0)
            ymax = tf.maximum(ymax - tf.cast(crop_h, tf.float32), 0)
            xmin = tf.maximum(xmin - tf.cast(crop_w, tf.float32), 0) 
            xmax = tf.maximum(xmax - tf.cast(crop_w, tf.float32), 0)

    # flip
    if flip_prob is not None:
        flip_td_prob = tf.random_uniform([], 0., 1.)
        flip_lr_prob = tf.random_uniform([], 0., 1.)

        # flip image
        image = tf.cond(
            tf.less(flip_td_prob, flip_prob[0]),
            lambda: tf.reverse(image, [0]),  # top-down flip
            lambda: image
        )
        image = tf.cond(
            tf.less(flip_lr_prob, flip_prob[1]),
            lambda: tf.reverse(image, [1]),  # left-right flip
            lambda: image
        )

        # flip ground truth coords
        if ground_truth is not None:
            ymax, ymin = tf.cond(
                tf.less(flip_td_prob, flip_prob[0]),
                lambda: (output_h - ymin -1., output_h - ymax -1.),
                lambda: (ymax, ymin)
            )
            xmax, xmin = tf.cond(
                tf.less(flip_lr_prob, flip_prob[1]),
                lambda: (output_w - xmin -1., output_w - xmax - 1.),
                lambda: (xmax, xmin)
            )

    # color jitter
    if color_jitter_prob is not None:
        bcs = tf.random_uniform([3], 0., 1.)
        # brightness
        image = tf.cond(bcs[0] < color_jitter_prob,
                        lambda: tf.image.adjust_brightness(image, tf.random_uniform([], 0., 0.3)),
                        lambda: image
                )

        # contrast
        image = tf.cond(bcs[1] < color_jitter_prob,
                        lambda: tf.image.adjust_contrast(image, tf.random_uniform([], 0.8, 1.2)),
                        lambda: image
                )
        
        # hue
        image = tf.cond(bcs[2] < color_jitter_prob,
                        lambda: tf.image.adjust_hue(image, tf.random_uniform([], -0.1, 0.1)),
                        lambda: image
                )

    # rotate
    if rotate is not None:
        angles = tf.random_uniform([], rotate[1], rotate[2]) * 3.1415926 / 180.  # to radian

        # rotate image
        IGNORE_LABEL = 255
        image = tf.subtract(image, IGNORE_LABEL)  # for fill value = 255
        image = tf.contrib.image.rotate(image, angles, 'BILINEAR')
        image = tf.add(image, IGNORE_LABEL)

        # rotate ground truth coords
        if ground_truth is not None:
            angles = -angles

            # center x, y
            rotate_center_x = (output_w - 1.) / 2.
            rotate_center_y = (output_h - 1.) / 2.
            offset_x = rotate_center_x * (1-tf.cos(angles)) + rotate_center_y * tf.sin(angles)
            offset_y = rotate_center_y * (1-tf.cos(angles)) - rotate_center_x * tf.sin(angles)

            # compute corner coords
            xminymin_x = xmin * tf.cos(angles) - ymin * tf.sin(angles) + offset_x
            xminymin_y = xmin * tf.sin(angles) + ymin * tf.cos(angles) + offset_y

            xmaxymax_x = xmax * tf.cos(angles) - ymax * tf.sin(angles) + offset_x
            xmaxymax_y = xmax * tf.sin(angles) + ymax * tf.cos(angles) + offset_y

            xminymax_x = xmin * tf.cos(angles) - ymax * tf.sin(angles) + offset_x
            xminymax_y = xmin * tf.sin(angles) + ymax * tf.cos(angles) + offset_y

            xmaxymin_x = xmax * tf.cos(angles) - ymin * tf.sin(angles) + offset_x
            xmaxymin_y = xmax * tf.sin(angles) + ymin * tf.cos(angles) + offset_y

            # new ymin, ymax, xmin, xmax
            xmin = tf.reduce_min(tf.concat([xminymin_x, xmaxymax_x, xminymax_x, xmaxymin_x], axis=-1), axis=-1, keepdims=True)
            ymin = tf.reduce_min(tf.concat([xminymin_y, xmaxymax_y, xminymax_y, xmaxymin_y], axis=-1), axis=-1, keepdims=True)
            xmax = tf.reduce_max(tf.concat([xminymin_x, xmaxymax_x, xminymax_x, xmaxymin_x], axis=-1), axis=-1, keepdims=True)
            ymax = tf.reduce_max(tf.concat([xminymin_y, xmaxymax_y, xminymax_y, xmaxymin_y], axis=-1), axis=-1, keepdims=True)

    # transpose back to CHW
    if data_format == 'channels_first':
        image = tf.transpose(image, [2, 0, 1])

    # check bounds and clipping
    if ground_truth is not None:
        # new center
        y_center = (ymin + ymax) / 2.
        x_center = (xmin + xmax) / 2.

        # check centers' bounds, [0, h-1], [0, w-1]
        # discard objs that center out of bounds
        y_mask = tf.cast(y_center > 0., tf.float32) * tf.cast(y_center < output_h - 1., tf.float32)
        x_mask = tf.cast(x_center > 0., tf.float32) * tf.cast(x_center < output_w - 1., tf.float32)
        mask = tf.reshape((x_mask * y_mask) > 0., [-1])

        ymin = tf.boolean_mask(ymin, mask)
        xmin = tf.boolean_mask(xmin, mask)
        ymax = tf.boolean_mask(ymax, mask)
        xmax = tf.boolean_mask(xmax, mask)
        class_id = tf.boolean_mask(class_id, mask)

        # clipping bounds
        ymin = tf.where(ymin < 0., ymin - ymin, ymin)
        xmin = tf.where(xmin < 0., xmin - xmin, xmin)
        ymax = tf.where(ymax < 0., ymax - ymax, ymax)
        xmax = tf.where(xmax < 0., xmax - xmax, xmax)
        ymin = tf.where(ymin > output_h - 1., ymin - ymin + output_h - 1., ymin)
        xmin = tf.where(xmin > output_w - 1., xmin - xmin + output_w - 1., xmin)
        ymax = tf.where(ymax > output_h - 1., ymax - ymax + output_h - 1., ymax)
        xmax = tf.where(xmax > output_w - 1., xmax - xmax + output_w - 1., xmax)

        # final center and h, w
        y = (ymin + ymax) / 2.
        x = (xmin + xmax) / 2.
        h = ymax - ymin
        w = xmax - xmin
        ground_truth_ = tf.concat([y, x, h, w, class_id], axis=-1)

        # pad to a fixed number of boxes
        if tf.shape(ground_truth_)[0] == 0:
            if pad_truth_to is not None:
                # pad input ground truth
                ground_truth_ = tf.concat([yy, xx, hh, ww, class_id], axis=-1)
                ground_truth = tf.pad(
                                ground_truth_, [[0, pad_truth_to-tf.shape(ground_truth)[0]], [0, 0]],
                                constant_values=-1.0
                            )
            else:
                # original gt, without padding
                ground_truth = tf.concat([yy, xx, hh, ww, class_id], axis=-1)

            return image_copy, ground_truth  # original image and label(ycenter, xcenter, h, w)
        else:
            if pad_truth_to is not None:
                # pad final ground truth
                ground_truth = tf.pad(
                                ground_truth_, [[0, pad_truth_to-tf.shape(ground_truth_)[0]], [0, 0]],
                                constant_values=-1.0
                            )
            else:
                # new gt, without padding
                ground_truth = tf.concat([y, x, h, w, class_id], axis=-1)

            return image, ground_truth
    # no gt
    else:
        return image


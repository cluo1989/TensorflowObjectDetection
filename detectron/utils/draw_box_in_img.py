# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division

import numpy as np

from PIL import Image, ImageDraw, ImageFont
import cv2

# from libs.configs import cfgs
# from libs.label_name_dict.label_dict import LABEL_NAME_MAP
NOT_DRAW_BOXES = 0
ONLY_DRAW_BOXES = -1
ONLY_DRAW_BOXES_WITH_SCORES = -2
LABEL_NAME_MAP = {
    0:'VAT_electronic_invoice',
    1:'VAT_roll_invoice',
    2:'VAT_general_invoice',
    3:'VAT_special_invoice',
    4:'Air_electronic_itinerary',
    5:'Train_ticket',
    6:'Taxi_ticket',
    7:'Passenger_transport_ticket',
    8:'Road_Bridge_ticket',
    9:'General_invoice',
    10:'Quota_invoice',
    11:'Car_sales_invoice',
    12:'Others',
}
STANDARD_COLORS = [
    'AliceBlue', 'Chartreuse', 'Aqua', 'Aquamarine', 'Azure', 'Beige', 'Bisque',
    'BlanchedAlmond', 'BlueViolet', 'BurlyWood', 'CadetBlue', 'AntiqueWhite',
    'Chocolate', 'Coral', 'CornflowerBlue', 'Cornsilk', 'Crimson', 'Cyan',
    'DarkCyan', 'DarkGoldenRod', 'DarkGrey', 'DarkKhaki', 'DarkOrange',
    'DarkOrchid', 'DarkSalmon', 'DarkSeaGreen', 'DarkTurquoise', 'DarkViolet',
    'DeepPink', 'DeepSkyBlue', 'DodgerBlue', 'FireBrick', 'FloralWhite',
    'ForestGreen', 'Fuchsia', 'Gainsboro', 'GhostWhite', 'Gold', 'GoldenRod',
    'Salmon', 'Tan', 'HoneyDew', 'HotPink', 'IndianRed', 'Ivory', 'Khaki',
    'Lavender', 'LavenderBlush', 'LawnGreen', 'LemonChiffon', 'LightBlue',
    'LightCoral', 'LightCyan', 'LightGoldenRodYellow', 'LightGray', 'LightGrey',
    'LightGreen', 'LightPink', 'LightSalmon', 'LightSeaGreen', 'LightSkyBlue',
    'LightSlateGray', 'LightSlateGrey', 'LightSteelBlue', 'LightYellow', 'Lime',
    'LimeGreen', 'Linen', 'Magenta', 'MediumAquaMarine', 'MediumOrchid',
    'MediumPurple', 'MediumSeaGreen', 'MediumSlateBlue', 'MediumSpringGreen',
    'MediumTurquoise', 'MediumVioletRed', 'MintCream', 'MistyRose', 'Moccasin',
    'NavajoWhite', 'OldLace', 'Olive', 'OliveDrab', 'Orange', 'OrangeRed',
    'Orchid', 'PaleGoldenRod', 'PaleGreen', 'PaleTurquoise', 'PaleVioletRed',
    'PapayaWhip', 'PeachPuff', 'Peru', 'Pink', 'Plum', 'PowderBlue', 'Purple',
    'Red', 'RosyBrown', 'RoyalBlue', 'SaddleBrown', 'Green', 'SandyBrown',
    'SeaGreen', 'SeaShell', 'Sienna', 'Silver', 'SkyBlue', 'SlateBlue',
    'SlateGray', 'SlateGrey', 'Snow', 'SpringGreen', 'SteelBlue', 'GreenYellow',
    'Teal', 'Thistle', 'Tomato', 'Turquoise', 'Violet', 'Wheat', 'White',
    'WhiteSmoke', 'Yellow', 'YellowGreen', 'LightBlue', 'LightGreen'
]
FONT = ImageFont.load_default()


def draw_a_rectangel_in_img(draw_obj, box, color, width):
    '''
    use draw lines to draw rectangle. since the draw_rectangle func can not modify the width of rectangle
    :param draw_obj:
    :param box: [x1, y1, x2, y2]
    :return:
    '''
    # x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
    # x1, y1, x2, y2 = box[2], box[0], box[3], box[1]
    x1 = int(box[1] - box[3]/2)
    y1 = int(box[0] - box[2]/2)
    x2 = int(box[1] + box[3]/2)
    y2 = int(box[0] + box[2]/2)
    top_left, top_right = (x1, y1), (x2, y1)
    bottom_left, bottom_right = (x1, y2), (x2, y2)

    draw_obj.line(xy=[top_left, top_right],
                  fill=color,
                  width=width)
    draw_obj.line(xy=[top_left, bottom_left],
                  fill=color,
                  width=width)
    draw_obj.line(xy=[bottom_left, bottom_right],
                  fill=color,
                  width=width)
    draw_obj.line(xy=[top_right, bottom_right],
                  fill=color,
                  width=width)


def only_draw_scores(draw_obj, box, score, color):

    # x, y = box[0], box[1]
    # x, y = box[2], box[0]
    x, y = int(box[1] - box[3]/2), int(box[0] - box[2]/2)
    draw_obj.rectangle(xy=[x, y, x+60, y+10],
                       fill=color)
    draw_obj.text(xy=(x, y),
                  text="obj:" +str(round(score, 2)),
                  fill='black',
                  font=FONT)


def draw_label_with_scores(draw_obj, box, label, score, color):
    txt = LABEL_NAME_MAP[label] + ':' + str(round(score, 2))

    # x, y = box[0], box[1]
    # x, y = box[2], box[0]
    x, y = int(box[1] - box[3]/2), int(box[0] - box[2]/2)
    draw_obj.rectangle(xy=[x, y, x + 6*len(txt), y + 10],
                       fill=color)
    draw_obj.text(xy=(x, y),
                  text=txt,
                  fill='black',
                  font=FONT)


def draw_boxes_with_label_and_scores(img_array, boxes, labels, scores, in_graph=True):
    # if in_graph:
    #     if cfgs.NET_NAME in ['resnet152_v1d', 'resnet101_v1d', 'resnet50_v1d']:
    #         img_array = (img_array * np.array(cfgs.PIXEL_STD) + np.array(cfgs.PIXEL_MEAN_)) * 255
    #     else:
    #         img_array = img_array + np.array(cfgs.PIXEL_MEAN)
    img_array = img_array + [123.68, 116.779, 103.979]
    img_array.astype(np.float32)
    boxes = boxes.astype(np.int64)
    labels = labels.astype(np.int32)
    img_array = np.array(img_array * 255 / np.max(img_array), dtype=np.uint8)

    img_obj = Image.fromarray(img_array)
    raw_img_obj = img_obj.copy()

    draw_obj = ImageDraw.Draw(img_obj)
    num_of_objs = 0
    for box, a_label, a_score in zip(boxes, labels, scores):

        # if a_label != NOT_DRAW_BOXES:  # 0
        if a_label == ONLY_DRAW_BOXES:  # -1
            continue
        elif a_label == ONLY_DRAW_BOXES_WITH_SCORES:  # -2
            only_draw_scores(draw_obj, box, a_score, color='purple')  # 'White'
            continue
        else:
            num_of_objs += 1
            draw_a_rectangel_in_img(draw_obj, box, color='red', width=3)#STANDARD_COLORS[a_label]
            draw_label_with_scores(draw_obj, box, a_label, a_score, color='purple')  # 'White'

    out_img_obj = Image.blend(raw_img_obj, img_obj, alpha=0.7)

    return np.array(out_img_obj)


# if __name__ == '__main__':
#     img_array = cv2.imread("/home/yjr/PycharmProjects/FPN_TF/tools/inference_image/2.jpg")
#     img_array = np.array(img_array, np.float32) - np.array(cfgs.PIXEL_MEAN)
#     boxes = np.array(
#         [[200, 200, 500, 500],
#          [300, 300, 400, 400],
#          [200, 200, 400, 400]]
#     )

#     # test only draw boxes
#     labes = np.ones(shape=[len(boxes), ], dtype=np.float32) * ONLY_DRAW_BOXES
#     scores = np.zeros_like(labes)
#     imm = draw_boxes_with_label_and_scores(img_array, boxes, labes ,scores)
#     # imm = np.array(imm)

#     cv2.imshow("te", imm)

#     # test only draw scores
#     labes = np.ones(shape=[len(boxes), ], dtype=np.float32) * ONLY_DRAW_BOXES_WITH_SCORES
#     scores = np.random.rand((len(boxes))) * 10
#     imm2 = draw_boxes_with_label_and_scores(img_array, boxes, labes, scores)

#     cv2.imshow("te2", imm2)
#     # test draw label and scores

#     labels = np.arange(1, 4)
#     imm3 = draw_boxes_with_label_and_scores(img_array, boxes, labels, scores)
#     cv2.imshow("te3", imm3)

#     cv2.waitKey(0)








from unittest import TestCase

import numpy as np
from skimage.io import imsave

from biaflows.exporter import mask_to_objects_2d, mask_to_objects_3d, representative_point
from shapely.geometry import Polygon, box, LineString

from biaflows.exporter.export_util import draw_linestring
from biaflows.exporter.skeleton_mask_to_objects import skeleton_mask_to_objects_2d, skeleton_mask_to_objects_3d
from tests.exporter.util import draw_square_by_corner, draw_poly


class TestMaskToObject2D(TestCase):
    def testExportOneSquare(self):
        image = np.zeros([300, 200], dtype=np.uint8)
        image = draw_square_by_corner(image, 100, (150, 50), color=255)

        slices = mask_to_objects_2d(image)

        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0].label, 255)
        self.assertTrue(slices[0].polygon.equals(box(50, 150, 151, 251)), msg="Polygon is equal")

    def testOffset(self):
        image = np.zeros([300, 200], dtype=np.uint8)
        image = draw_square_by_corner(image, 100, (150, 50), color=255)

        slices = mask_to_objects_2d(image, offset=(255, 320))

        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0].label, 255)
        self.assertTrue(slices[0].polygon.equals(box(305, 470, 406, 571)), msg="Polygon is equal")

    def testSeveralObjects(self):
        image = np.zeros([300, 200], dtype=np.uint8)
        image = draw_square_by_corner(image, 50, (150, 50), color=255)
        image = draw_square_by_corner(image, 50, (205, 105), color=127)

        slices = mask_to_objects_2d(image)
        # sort by bounding box top left corner
        slices = sorted(slices, key=lambda s: s.polygon.bounds[:2])

        self.assertEqual(len(slices), 2)
        self.assertEqual(slices[0].label, 255)
        self.assertTrue(slices[0].polygon.equals(box(50, 150, 101, 201)), msg="Polygon is equal")
        self.assertEqual(slices[1].label, 127)
        self.assertTrue(slices[1].polygon.equals(box(105, 205, 156, 256)), msg="Polygon is equal")

    def testMultipartPolygon(self):
        image = np.zeros([300, 200], dtype=np.uint8)
        image = draw_square_by_corner(image, 50, (150, 50), color=255)
        image = draw_square_by_corner(image, 50, (201, 101), color=127)

        slices = mask_to_objects_2d(image)
        # sort by bounding box top left corner
        slices = sorted(slices, key=lambda s: s.polygon.bounds[:2])

        self.assertEqual(len(slices), 2)
        self.assertEqual(slices[0].label, 255)
        self.assertEqual(slices[1].label, 127)

    def testAdjacentWithoutSeperation(self):
        image = np.zeros([300, 200], dtype=np.uint8)
        image = draw_square_by_corner(image, 50, (150, 50), color=255)
        image = draw_square_by_corner(image, 50, (150, 101), color=127)

        slices = mask_to_objects_2d(image)
        # sort by bounding box top left corner
        slices = sorted(slices, key=lambda s: s.polygon.bounds[:2])

        self.assertEqual(len(slices), 2)
        self.assertEqual(slices[0].label, 255)
        self.assertEqual(slices[1].label, 127)

    def testAdjacentWithSeparation(self):
        image = np.zeros([300, 200], dtype=np.uint8)
        image = draw_square_by_corner(image, 50, (150, 50), color=255)
        image = draw_square_by_corner(image, 50, (150, 102), color=127)

        slices = mask_to_objects_2d(image)
        # sort by bounding box top left corner
        slices = sorted(slices, key=lambda s: s.polygon.bounds[:2])

        self.assertEqual(len(slices), 2)
        self.assertEqual(slices[0].label, 255)
        self.assertTrue(slices[0].polygon.equals(box(50, 150, 101, 201)), msg="Polygon is equal")
        self.assertEqual(slices[1].label, 127)
        self.assertTrue(slices[1].polygon.equals(box(102, 150, 153, 201)), msg="Polygon is equal")

    def testSmallObject(self):
        image = np.zeros([100, 100], dtype=np.uint8)
        image = draw_poly(image, Polygon([(15, 77), (15, 78), (16, 78), (15, 77)]), color=127)
        image = draw_poly(image, box(1, 1, 2, 2), color=255)

        slices = mask_to_objects_2d(image)
        # sort by bounding box top left corner
        slices = sorted(slices, key=lambda s: s.polygon.bounds[:2])

        self.assertEqual(len(slices), 2)
        self.assertEqual(slices[0].label, 255)
        self.assertEqual(slices[1].label, 127)

    def testOtherPixels(self):
        mask = np.array([
            [0, 0, 0, 0, 0, 0],
            [0, 1, 1, 0, 1, 1],
            [0, 0, 1, 0, 1, 0],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0]
        ])
        p1 = Polygon([(1, 1), (1, 2), (2, 2), (2, 3), (3, 3), (3, 1), (1, 1)])
        p2 = Polygon([(4, 1), (4, 3), (5, 3), (5, 2), (6, 2), (6, 1), (4, 1)])
        p3 = Polygon([(3, 3), (3, 4), (4, 4), (4, 3), (3, 3)])
        slices = mask_to_objects_2d(mask)
        self.assertEqual(len(slices), 3)
        self.assertTrue(slices[0].polygon.equals(p1))
        self.assertTrue(slices[1].polygon.equals(p2))
        self.assertTrue(slices[2].polygon.equals(p3))

    def testTwoPoints(self):
        mask = np.array([
            [0, 0, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 0, 0]
        ])
        polygon = Polygon([(1, 1), (1, 2), (3, 2), (3, 1), (1, 1)])
        slices = mask_to_objects_2d(mask)
        self.assertEqual(len(slices), 1)
        self.assertTrue(slices[0].polygon.equals(polygon))

    def testRepresentativePoint(self):
        image = np.zeros([300, 200], dtype=np.uint8)
        image = draw_square_by_corner(image, 50, (150, 50), color=255)
        slices = mask_to_objects_2d(image)

        x, y = representative_point(slices[0].polygon, image, label=255)
        self.assertEqual(image[y, x], 255)

class TestMaskToObject3D(TestCase):
    def testTwoObjectsOneSpanning(self):
        image = np.zeros([100, 200, 3], dtype=np.uint8)
        image[:, :, 0] = draw_square_by_corner(image[:, :, 0], 10, (5, 10), 100)
        image[:, :, 1] = draw_square_by_corner(image[:, :, 1], 10, (5, 10), 100)
        image[:, :, 2] = draw_square_by_corner(image[:, :, 2], 12, (5, 10), 100)
        image[:, :, 1] = draw_square_by_corner(image[:, :, 1], 25, (45, 40), 200)
        slices = mask_to_objects_3d(image, assume_unique_labels=True)

        self.assertIsInstance(slices, list)
        self.assertEqual(len(slices), 2, msg="found 2 objects")

        fslice1 = [sl for sl in slices if len(sl) > 1]
        self.assertEqual(len(fslice1), 1, msg="there is exactly one object with more than one slice")
        slice1 = fslice1[0]
        self.assertEqual(slice1[0].label, 100)
        self.assertEqual(slice1[0].depth, 0)
        self.assertTrue(slice1[0].polygon.equals(box(10, 5, 21, 16)))
        self.assertEqual(slice1[1].label, 100)
        self.assertEqual(slice1[1].depth, 1)
        self.assertTrue(slice1[1].polygon.equals(box(10, 5, 21, 16)))
        self.assertEqual(slice1[2].label, 100)
        self.assertEqual(slice1[2].depth, 2)
        self.assertTrue(slice1[2].polygon.equals(box(10, 5, 23, 18)))

        fslice2 = [sl for sl in slices if len(sl) == 1]
        self.assertEqual(len(fslice2), 1, msg="there is exactly one object with one slice")
        slice2 = fslice2[0]
        self.assertEqual(len(slice2), 1)
        self.assertEqual(slice2[0].label, 200)
        self.assertEqual(slice2[0].depth, 1)
        self.assertTrue(slice2[0].polygon.equals(box(40, 45, 66, 71)))


class TestSkeletonMaskToObject(TestCase):
    def testSkeletonMask2D(self):
        image = np.zeros([40, 40], dtype=np.uint8)
        image = draw_linestring(image, linestring=LineString([(5, 5), (18, 10), (30, 30), (5, 30)]))
        image = draw_linestring(image, linestring=LineString([(5, 25), (25, 5)]))
        slices = skeleton_mask_to_objects_2d(image)
        self.assertEqual(1, len(slices))

    def testSkeletonMask3D(self):
        image = np.zeros([40, 40, 40], dtype=np.uint8)
        image[20, :, :] = draw_linestring(image[20, :, :], LineString([(5, 5), (25, 25)]))
        image[:, 25, :] = draw_linestring(image[:, 25, :], LineString([(5, 5), (25, 25)]), color=127)
        image[:, :, 30] = draw_linestring(image[:, :, 30], LineString([(5, 5), (25, 25)]), color=63)
        slices = skeleton_mask_to_objects_3d(image, assume_unique_labels=True)
        self.assertEqual(3, len(slices))

        slices = sorted(slices, key=lambda s: s[0].label)

        self.assertEqual(1, len(slices[0]))
        self.assertEqual(63, slices[0][0].label)
        self.assertEqual(21, len(slices[1]))
        self.assertEqual(127, slices[1][0].label)
        self.assertEqual(21, len(slices[2]))
        self.assertEqual(255, slices[2][0].label)

    def testSkeletonMask3DProjection(self):
        image = np.zeros([30, 30, 30], dtype=np.uint8)
        image[:, :, 15] = draw_linestring(image[:, :, 15], LineString([(5, 5), (25, 25)]))
        slices = skeleton_mask_to_objects_3d(image, assume_unique_labels=True, projection=3)
        self.assertEqual(1, len(slices))
        self.assertEqual(7, len(slices[0]))

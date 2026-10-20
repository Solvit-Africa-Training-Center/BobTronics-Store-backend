import base64

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role

from .models import Category, Product, ProductImage

User = get_user_model()


def uploaded_test_image():
    content = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jQWQAAAAASUVORK5CYII="
    )
    return SimpleUploadedFile("test.png", content, content_type="image/png")


class CatalogTestBase(APITestCase):
    """Shared data: one admin, one customer, 2 categories, 3 products."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="admin@bobtronics.test",
            password="StrongPass123!",
            first_name="Ada",
            last_name="Admin",
            role=Role.ADMIN,
        )
        cls.customer = User.objects.create_user(
            email="customer@bobtronics.test",
            password="StrongPass123!",
            first_name="Cora",
            last_name="Customer",
            role=Role.CUSTOMER,
        )

        cls.phones = Category.objects.create(
            name="Phones", description="Smartphones"
        )
        cls.laptops = Category.objects.create(
            name="Laptops", description="Notebooks"
        )

        cls.phone = Product.objects.create(
            category=cls.phones,
            name="Galaxy X",
            description="Flagship phone",
            brand="Samsung",
            price="500.00",
            stock_quantity=10,
            warranty="1 year",
            is_available=True,
        )
        cls.laptop = Product.objects.create(
            category=cls.laptops,
            name="ThinkBook 14",
            description="Business laptop",
            brand="Lenovo",
            price="900.00",
            stock_quantity=0,
            warranty="2 years",
            is_available=True,
        )
        cls.hidden = Product.objects.create(
            category=cls.phones,
            name="Old Phone",
            description="Discontinued",
            brand="Nokia",
            price="50.00",
            stock_quantity=5,
            warranty="none",
            is_available=False,
        )

        cls.primary_image = ProductImage.objects.create(
            product=cls.phone,
            image_file=uploaded_test_image(),
            is_primary=True,
        )
        ProductImage.objects.create(
            product=cls.phone,
            image_file=uploaded_test_image(),
            is_primary=False,
        )


class PublicCatalogTests(CatalogTestBase):
    def test_anonymous_can_list_categories(self):
        response = self.client.get(reverse("category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # categories are not paginated, so the response is a plain list
        names = [c["name"] for c in response.data]
        self.assertEqual(names, ["Laptops", "Phones"])

    def test_product_list_is_paginated(self):
        response = self.client.get(reverse("product-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, response.data)

    def test_unavailable_products_are_hidden(self):
        response = self.client.get(reverse("product-list"))
        names = [p["name"] for p in response.data["results"]]
        self.assertIn("Galaxy X", names)
        self.assertNotIn("Old Phone", names)

    def test_hidden_product_detail_is_404(self):
        url = reverse("product-detail", args=[self.hidden.pk])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_product_detail_includes_images(self):
        url = reverse("product-detail", args=[self.phone.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["images"]), 2)
        self.assertEqual(response.data["category_name"], "Phones")

    def test_list_shows_primary_image(self):
        response = self.client.get(reverse("product-list"), {"search": "Galaxy"})
        self.assertIn(
            "/media/product-images/",
            response.data["results"][0]["primary_image"],
        )

    def test_search_by_brand(self):
        response = self.client.get(reverse("product-list"), {"search": "lenovo"})
        names = [p["name"] for p in response.data["results"]]
        self.assertEqual(names, ["ThinkBook 14"])

    def test_filter_by_category(self):
        response = self.client.get(
            reverse("product-list"), {"category": self.laptops.pk}
        )
        names = [p["name"] for p in response.data["results"]]
        self.assertEqual(names, ["ThinkBook 14"])

    def test_filter_by_price_range(self):
        response = self.client.get(
            reverse("product-list"), {"min_price": 600, "max_price": 1000}
        )
        names = [p["name"] for p in response.data["results"]]
        self.assertEqual(names, ["ThinkBook 14"])

    def test_filter_in_stock(self):
        response = self.client.get(reverse("product-list"), {"in_stock": "true"})
        names = [p["name"] for p in response.data["results"]]
        self.assertEqual(names, ["Galaxy X"])

    def test_ordering_by_price(self):
        cheapest_first = self.client.get(
            reverse("product-list"), {"ordering": "price"}
        )
        self.assertEqual(
            [p["name"] for p in cheapest_first.data["results"]],
            ["Galaxy X", "ThinkBook 14"],
        )
        dearest_first = self.client.get(
            reverse("product-list"), {"ordering": "-price"}
        )
        self.assertEqual(
            [p["name"] for p in dearest_first.data["results"]],
            ["ThinkBook 14", "Galaxy X"],
        )

    def test_category_products_action(self):
        url = reverse("category-products", args=[self.phones.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["results"]]
        self.assertEqual(names, ["Galaxy X"])  # hidden product excluded

    def test_public_endpoints_are_read_only(self):
        response = self.client.post(
            reverse("category-list"), {"name": "Hacked"}, format="json"
        )
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


class AdminCatalogPermissionTests(CatalogTestBase):
    def test_anonymous_is_rejected(self):
        response = self.client.get(reverse("admin-category-list"))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer)
        for name in ("admin-category-list", "admin-product-list", "admin-image-list"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, name)

    def test_customer_cannot_create_category(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("admin-category-list"), {"name": "Nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Category.objects.filter(name="Nope").exists())

    def test_admin_is_allowed(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("admin-category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_admin_is_rejected(self):
        self.admin.is_active = False
        self.admin.save()
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("admin-category-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminCatalogCrudTests(CatalogTestBase):
    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_create_category(self):
        response = self.client.post(
            reverse("admin-category-list"),
            {"name": "Tablets", "description": "Tablet computers"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name="Tablets").exists())

    def test_category_name_must_be_unique(self):
        response = self.client.post(
            reverse("admin-category-list"), {"name": "Phones"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_category(self):
        url = reverse("admin-category-detail", args=[self.phones.pk])
        response = self.client.patch(
            url, {"description": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.phones.refresh_from_db()
        self.assertEqual(self.phones.description, "Updated")

    def test_create_product(self):
        response = self.client.post(
            reverse("admin-product-list"),
            {
                "category": self.laptops.pk,
                "name": "MacBook Air",
                "description": "Thin laptop",
                "brand": "Apple",
                "price": "1200.00",
                "stock_quantity": 4,
                "warranty": "1 year",
                "is_available": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(name="MacBook Air").exists())

    def test_admin_list_includes_unavailable_products(self):
        response = self.client.get(reverse("admin-product-list"))
        names = [p["name"] for p in response.data["results"]]
        self.assertIn("Old Phone", names)

    def test_update_product_stock(self):
        url = reverse("admin-product-detail", args=[self.phone.pk])
        response = self.client.patch(url, {"stock_quantity": 99}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.phone.refresh_from_db()
        self.assertEqual(self.phone.stock_quantity, 99)

    def test_delete_product(self):
        url = reverse("admin-product-detail", args=[self.hidden.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=self.hidden.pk).exists())

    def test_new_primary_image_unsets_the_old_one(self):
        response = self.client.post(
            reverse("admin-image-list"),
            {
                "product": self.phone.pk,
                "image_file": uploaded_test_image(),
                "is_primary": True,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.primary_image.refresh_from_db()
        self.assertFalse(self.primary_image.is_primary)
        self.assertEqual(
            ProductImage.objects.filter(product=self.phone, is_primary=True).count(),
            1,
        )

    def test_filter_images_by_product(self):
        response = self.client.get(
            reverse("admin-image-list"), {"product": self.phone.pk}
        )
        self.assertEqual(response.data["count"], 2)


class ProductValidationTests(CatalogTestBase):
    def setUp(self):
        self.client.force_authenticate(self.admin)

    def product_payload(self, **overrides):
        data = {
            "category": self.laptops.pk,
            "name": "MacBook Air",
            "description": "Thin laptop",
            "brand": "Apple",
            "price": "1200.00",
            "stock_quantity": 4,
            "warranty": "1 year",
            "is_available": True,
        }
        data.update(overrides)
        return data

    # ---- categories ----

    def test_category_name_is_unique_ignoring_case(self):
        response = self.client.post(
            reverse("admin-category-list"), {"name": "phones"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_name_is_trimmed(self):
        response = self.client.post(
            reverse("admin-category-list"),
            {"name": "   Smart   Watches  "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Smart Watches")

    def test_category_name_too_short(self):
        response = self.client.post(
            reverse("admin-category-list"), {"name": "A"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_can_keep_its_own_name_on_update(self):
        url = reverse("admin-category-detail", args=[self.phones.pk])
        response = self.client.patch(url, {"name": "Phones"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ---- products ----

    def test_price_zero_is_rejected(self):
        response = self.client.post(
            reverse("admin-product-list"),
            self.product_payload(price="0.00"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", response.data)

    def test_negative_price_is_rejected(self):
        response = self.client.post(
            reverse("admin-product-list"),
            self.product_payload(price="-5.00"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_stock_is_rejected(self):
        response = self.client.post(
            reverse("admin-product-list"),
            self.product_payload(stock_quantity=-1),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stock_quantity", response.data)

    def test_absurd_stock_is_rejected(self):
        response = self.client.post(
            reverse("admin-product-list"),
            self.product_payload(stock_quantity=5_000_000),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_product_is_rejected_ignoring_case(self):
        response = self.client.post(
            reverse("admin-product-list"),
            self.product_payload(
                category=self.phones.pk, name="galaxy x", brand="SAMSUNG"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_same_name_in_another_category_is_allowed(self):
        response = self.client.post(
            reverse("admin-product-list"),
            self.product_payload(
                category=self.laptops.pk, name="Galaxy X", brand="Samsung"
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_product_can_be_updated_without_tripping_duplicate_rule(self):
        url = reverse("admin-product-detail", args=[self.phone.pk])
        response = self.client.patch(url, {"price": "450.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_name_is_trimmed(self):
        response = self.client.post(
            reverse("admin-product-list"),
            self.product_payload(name="  MacBook    Pro  "),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "MacBook Pro")

    # ---- images ----

    def test_image_url_is_not_accepted(self):
        response = self.client.post(
            reverse("admin-image-list"),
            {"product": self.laptop.pk, "image_url": "javascript:alert(1)"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image_file", response.data)

    def test_image_file_is_required(self):
        response = self.client.post(
            reverse("admin-image-list"),
            {
                "product": self.phone.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_first_image_becomes_primary_automatically(self):
        response = self.client.post(
            reverse("admin-image-list"),
            {
                "product": self.laptop.pk,
                "image_file": uploaded_test_image(),
                "is_primary": False,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_primary"])

    def test_second_image_is_not_primary_by_default(self):
        response = self.client.post(
            reverse("admin-image-list"),
            {
                "product": self.phone.pk,
                "image_file": uploaded_test_image(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["is_primary"])

    def test_image_limit_per_product(self):
        # the phone already has 2 images, add 8 more to reach 10
        for i in range(8):
            ProductImage.objects.create(
                product=self.phone, image_file=uploaded_test_image()
            )
        response = self.client.post(
            reverse("admin-image-list"),
            {
                "product": self.phone.pk,
                "image_file": uploaded_test_image(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("product", response.data)

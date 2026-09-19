from mercaribot.models import MercariItem


def test_mercari_item_from_api_dict():
    api_data = {
        "id": "m999888777",
        "name": "Super Famicom Console",
        "price": "4500",
        "thumbnails": ["https://static.mercdn.net/item/detail/orig/photos/m999888777_1.jpg"],
        "status": "ITEM_STATUS_ON_SALE",
    }

    item = MercariItem.from_api_dict(api_data, keyword="famicom")
    assert item is not None
    assert item.id == "m999888777"
    assert item.name == "Super Famicom Console"
    assert item.price == 4500
    assert item.image_url == "https://static.mercdn.net/item/detail/orig/photos/m999888777_1.jpg"
    assert item.product_url == "https://jp.mercari.com/item/m999888777"
    assert item.keyword == "famicom"

    shops_data = {
        "id": "2JVKrTRZKhhngSvosFFT7n",
        "name": "Shop Item",
        "price": "900",
        "thumbnails": ["https://assets.mercari-shops-static.com/-/small/plain/sKsYHw.jpg@webp"],
    }
    shop_item = MercariItem.from_api_dict(shops_data, keyword="cd")
    assert shop_item is not None
    assert shop_item.product_url == "https://jp.mercari.com/shops/product/2JVKrTRZKhhngSvosFFT7n"


def test_mercari_item_invalid():
    assert MercariItem.from_api_dict({}) is None
    assert MercariItem.from_api_dict({"id": ""}) is None

from dataclasses import dataclass
from decimal import Decimal

from prompt_toolkit import prompt
from prompt_toolkit.validation import ValidationError
from psycopg.rows import class_row
from rich.table import Table
from rich.panel import Panel

from console import console, render_error
from db import get_conn
from validators import PriceValidator, NonEmptyValidator, YesNoValidator, PositiveIntValidator
from commands import command, CATEGORY_PRODUCTS


@dataclass
class Product:
    id: int
    sku: str
    name: str
    price: Decimal
    category_id: int


@dataclass
class ProductCategory:
    id: int
    category_name: str


def _render_product(product: Product) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Поле", style="bold cyan", width=12)
    table.add_column("Значение", style="white")
    table.add_row("ID", str(product.id))
    table.add_row("SKU", product.sku)
    table.add_row("Название", product.name)
    table.add_row("Цена", f"{product.price:.2f}")

    panel = Panel(table, expand=False, title=f"[bold green]Товар #{product.id}[/bold green]", border_style="green")
    console.print(panel)


@command("list product_categories", "список категорий товаров", CATEGORY_PRODUCTS)
def list_product_categories() -> None:
    conn = get_conn()
    table = Table(title="Категории", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Название категории", style="green")

    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories ORDER BY id")
        rows: list[ProductCategory] = cur.fetchall()

    for row in rows:
        table.add_row(str(row.id), row.category_name)
    console.print(table)


@command("show product_category", "информация о категории", CATEGORY_PRODUCTS)
def show_product_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        cat: ProductCategory | None = cur.fetchone()

    if cat is None:
        render_error(f"Категория с ID {_id} не найдена")
        return

    panel = Panel(f"[bold]{cat.category_name}[/bold]", title=f"Категория #{cat.id}", border_style="cyan")
    console.print(panel)


@command("add product_category", "добавить категорию товаров", CATEGORY_PRODUCTS)
def add_product_category() -> None:
    conn = get_conn()
    name = prompt("Название категории: ", validator=NonEmptyValidator()).strip()
    conn.execute("INSERT INTO catalog.product_categories (category_name) VALUES (%s)", (name,))
    console.print(f"[green]Категория '{name}' добавлена[/green]")


@command("edit product_category", "редактировать категорию", CATEGORY_PRODUCTS)
def edit_product_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        cat: ProductCategory | None = cur.fetchone()

    if cat is None:
        render_error(f"Категория с ID {_id} не найдена")
        return

    name = prompt("Название категории: ", default=cat.category_name, validator=NonEmptyValidator()).strip()
    conn.execute("UPDATE catalog.product_categories SET category_name = %s WHERE id = %s", (name, _id))
    console.print(f"[green]Категория #{_id} обновлена[/green]")


@command("delete product_category", "удалить категорию", CATEGORY_PRODUCTS)
def delete_product_category(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(ProductCategory)) as cur:
        cur.execute("SELECT * FROM catalog.product_categories WHERE id = %s", (_id,))
        cat: ProductCategory | None = cur.fetchone()

    if cat is None:
        render_error(f"Категория с ID {_id} не найдена")
        return

    console.print(Panel(f"[bold]{cat.category_name}[/bold]", title=f"Категория #{cat.id}"))
    answer = prompt("Вы уверены? (y/n): ", validator=YesNoValidator())
    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM catalog.product_categories WHERE id = %s", (_id,))
        console.print(f"[green]Категория #{_id} удалена[/green]")


@command("list products", "список всех товаров", CATEGORY_PRODUCTS)
def list_products() -> None:
    conn = get_conn()
    table = Table(title="Товары", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("SKU", style="green", min_width=10)
    table.add_column("Название", style="yellow", min_width=20)
    table.add_column("Цена", style="magenta", min_width=10)
    table.add_column("ID категории продукта", style="dim", width=10, justify="right")

    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products ORDER BY id")
        rows: list[Product] = cur.fetchall()

    for p in rows:
        price_str = f"{p.price:.2f}" if p.price is not None else ""
        table.add_row(str(p.id), p.sku, p.name, price_str, str(p.category_id))
    console.print(table)


@command("show product", "информация о товаре", CATEGORY_PRODUCTS)
def show_product(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    if product is None:
        render_error(f"Товар с ID {_id} не найден")
        return

    _render_product(product)


@command("add product", "добавить товар (интерактивно)", CATEGORY_PRODUCTS)
def add_product() -> None:
    conn = get_conn()
    sku = prompt("SKU: ", validator=NonEmptyValidator()).strip()
    name = prompt("Название: ", validator=NonEmptyValidator()).strip()
    price_text = prompt("Цена: ", validator=PriceValidator()).strip()
    price = Decimal(price_text) if price_text else None
    category_id_text = prompt("ID категории продукта: ", validator=PositiveIntValidator()).strip()
    category_id = int(product_category_text)

    conn.execute("INSERT INTO catalog.products (sku, name, price, category_id) VALUES (%s, %s, %s, %s)", (sku, name, price, category_id))
    console.print(f"[green]Товар '{name}' добавлен[/green]")


@command("edit product", "редактировать товар", CATEGORY_PRODUCTS)
def edit_product(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    if product is None:
        render_error(f"Товар с ID {_id} не найден")
        return

    sku = prompt("SKU: ", default=product.sku, validator=NonEmptyValidator()).strip()
    name = prompt("Название: ", default=product.name, validator=NonEmptyValidator()).strip()
    price_text = prompt("Цена: ", default=(str(product.price) if product.price is not None else ""), validator=PriceValidator()).strip()
    price = Decimal(price_text) if price_text else None
    category_id_text = prompt("ID категории продукта: ", default=(str(product.category_id)), validator=PositiveIntValidator()).strip()
    category_id = int(category_id_text)

    conn.execute("UPDATE catalog.products SET sku = %s, name = %s, price = %s, category_id = %s, WHERE id = %s", (sku, name, price, category_id, _id))
    console.print(f"[green]Товар #{_id} обновлен[/green]")


@command("delete product", "удалить товар", CATEGORY_PRODUCTS)
def delete_product(_id: str) -> None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(Product)) as cur:
        cur.execute("SELECT * FROM catalog.products WHERE id = %s", (_id,))
        product: Product | None = cur.fetchone()

    if product is None:
        render_error(f"Товар с ID {_id} не найден")
        return

    _render_product(product)
    answer = prompt("Вы уверены? (y/n): ", validator=YesNoValidator())
    if YesNoValidator.is_yes(answer):
        conn.execute("DELETE FROM catalog.products WHERE id = %s", (_id,))
        console.print(f"[green]Товар #{_id} удален[/green]")

"""
scraper.py — Google Maps Scraper con Playwright
Versión async generator para streaming SSE en Flask
Basado en scraper_api.py v2.0 (ya probado y funcional)
"""
import asyncio
import re
import sys
from playwright.async_api import async_playwright


def calc_opportunity_score(data: dict) -> int:
    """
    Score IA 0-100. Mayor = más probable que necesite nuestros servicios.
    """
    score = 0

    # Presencia web
    website = data.get('website', '')
    if not website:
        score += 40  # Sin web → urgente
    elif any(x in website.lower() for x in ['wix', 'blogspot', 'wordpress.com', 'weebly', 'jimdo', 'webnode']):
        score += 20  # Web básica/gratuita

    # Rating
    rating_str = data.get('rating', '')
    if not rating_str:
        score += 10  # Invisible online
    else:
        try:
            rating = float(rating_str.replace(',', '.'))
            if rating < 4.0:
                score += 20
            elif rating < 4.5:
                score += 10
        except:
            score += 5

    # Reseñas (pocas = negocio pequeño, más abierto)
    reviews_str = data.get('reviews', '')
    if reviews_str:
        try:
            reviews = int(re.sub(r'[^\d]', '', reviews_str))
            if reviews < 10:
                score += 15
            elif reviews < 50:
                score += 8
        except:
            pass
    else:
        score += 10

    # Tiene teléfono = podemos contactar (+15)
    if data.get('phone'):
        score += 15

    return min(score, 100)


def format_phone_argentina(raw: str) -> str:
    """Normaliza número a formato internacional argentina."""
    clean = re.sub(r'[^\d+]', '', raw)
    if clean.startswith('+'):
        return clean
    if clean.startswith('0'):
        return '+549' + clean[1:]
    if clean.startswith('11') or clean.startswith('15'):
        return '+549' + clean
    if len(clean) == 8:
        return '+54911' + clean
    return clean


async def run_scrape(search_query: str, max_results: int = 20):
    """
    Async generator que yield-ea datos de progreso y leads a medida que los extrae.
    Cada yield es un dict con 'type': 'progress' | 'lead'
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale='es-ES',
            geolocation={'longitude': -58.3816, 'latitude': -34.6037},
            permissions=['geolocation'],
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        yield {'type': 'progress', 'msg': f'🔍 Buscando: {search_query}', 'pct': 5}

        search_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(4)

        # Aceptar cookies si aparece
        try:
            await page.click('button:has-text("Aceptar todo")', timeout=3000)
            await asyncio.sleep(1)
        except:
            pass

        yield {'type': 'progress', 'msg': '📋 Cargando lista de negocios...', 'pct': 10}

        # Scroll para cargar resultados
        try:
            await page.wait_for_selector('a[href^="https://www.google.com/maps/place"]', timeout=12000)
            for _ in range(6):
                await page.mouse.wheel(delta_x=0, delta_y=8000)
                await asyncio.sleep(1.5)
        except:
            pass

        # Obtener URLs únicas
        urls = []
        links = await page.query_selector_all('a[href^="https://www.google.com/maps/place"]')
        for link in links:
            href = await link.get_attribute('href')
            if href and href not in urls:
                urls.append(href)
                if len(urls) >= max_results:
                    break

        if not urls:
            yield {'type': 'progress', 'msg': '⚠️ No se encontraron resultados. Probá con otro término.', 'pct': 100}
            await browser.close()
            return

        yield {'type': 'progress', 'msg': f'✅ {len(urls)} negocios encontrados. Extrayendo datos...', 'pct': 15}

        for idx, url in enumerate(urls):
            pct = 15 + int((idx / len(urls)) * 80)
            yield {
                'type': 'progress',
                'msg': f'⚙️ Procesando {idx + 1}/{len(urls)}...',
                'pct': pct
            }

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(2)

                data = {
                    'nombre': '', 'phone': '', 'website': '',
                    'address': '', 'category': '', 'rating': '',
                    'reviews': '', 'maps_url': url
                }

                # Nombre
                try:
                    el = await page.query_selector('h1')
                    data['nombre'] = (await el.inner_text()).strip() if el else ''
                except:
                    pass

                # Categoría
                try:
                    cat_el = await page.query_selector('button[jsaction*="category"]')
                    if not cat_el:
                        cat_el = await page.query_selector('button.DkEaL')
                    if cat_el:
                        data['category'] = (await cat_el.inner_text()).strip()
                except:
                    pass

                # Dirección
                try:
                    addr_els = await page.query_selector_all('button[data-item-id^="address"]')
                    if addr_els:
                        data['address'] = (await addr_els[0].inner_text()).strip()
                except:
                    pass

                # Teléfono
                try:
                    phone_els = await page.query_selector_all('button[data-item-id^="phone:tel:"]')
                    if phone_els:
                        raw = (await phone_els[0].inner_text()).strip()
                        data['phone'] = format_phone_argentina(raw)
                except:
                    pass

                # Website
                try:
                    links_page = await page.query_selector_all('a[href^="http"]')
                    for l in links_page:
                        href = await l.get_attribute('href')
                        if href and 'google.com' not in href and 'gstatic.com' not in href:
                            data['website'] = href
                            break
                except:
                    pass

                # Rating
                try:
                    rating_el = await page.query_selector('div[aria-label*="estrellas"]')
                    if rating_el:
                        aria = await rating_el.get_attribute('aria-label')
                        data['rating'] = aria.split(' ')[0] if aria else ''
                except:
                    pass

                # Reviews
                try:
                    rev_el = await page.query_selector('button[aria-label*="reseñas"]')
                    if rev_el:
                        data['reviews'] = re.sub(r'[^\d]', '', await rev_el.inner_text())
                except:
                    pass

                # Score y WhatsApp
                data['opportunity_score'] = calc_opportunity_score(data)
                data['whatsapp_link'] = (
                    f"https://wa.me/{data['phone'].replace('+', '')}"
                    if data['phone'] else ''
                )

                if data['nombre']:
                    yield {'type': 'lead', **data}

                await asyncio.sleep(1)

            except Exception as e:
                yield {'type': 'progress', 'msg': f'⚠️ Error en negocio {idx+1}: {str(e)[:60]}', 'pct': pct}
                continue

        await browser.close()
        yield {'type': 'progress', 'msg': '🎉 Prospección completada', 'pct': 100}

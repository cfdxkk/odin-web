import { resolveOdinLocale, SITE_COPY, type OdinLocale } from '~/lib/odin-copy'

export function useOdinLocale() {
  const route = useRoute()
  const locale = useState<OdinLocale>('odin-locale', () => resolveOdinLocale(typeof route.query.lang === 'string' ? route.query.lang : null))
  const copy = computed(() => SITE_COPY[locale.value])
  function setLocale(value: OdinLocale) {
    locale.value = value
    if (import.meta.client) {
      const url = new URL(window.location.href)
      url.searchParams.set('lang', value)
      window.history.replaceState(window.history.state, '', url)
      localStorage.setItem('odin-language', value)
    }
  }
  onMounted(() => {
    const requested = new URLSearchParams(window.location.search).get('lang')
    locale.value = resolveOdinLocale(requested || localStorage.getItem('odin-language'))
  })
  useHead(() => ({ htmlAttrs: { lang: locale.value === 'zh' ? 'zh-CN' : 'en' }, title: copy.value.pageTitle, meta: [{ name: 'description', content: copy.value.description }] }))
  return { locale, copy, setLocale }
}

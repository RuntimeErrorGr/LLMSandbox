import { onBeforeUnmount, onMounted, ref, shallowRef, type Ref, type ShallowRef } from 'vue'

interface Options<T> {
  interval?: number
  keepPolling?: (value: T | null) => boolean
}

export interface Resource<T> {
  data: ShallowRef<T | null>
  error: Ref<string | null>
  loading: Ref<boolean>
  refresh: () => Promise<void>
}

export function useResource<T>(loader: () => Promise<T>, options: Options<T> = {}): Resource<T> {
  const data = shallowRef<T | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)
  let timer: number | undefined
  let stopped = false

  function schedule() {
    window.clearTimeout(timer)
    if (stopped || !options.interval) return
    if (options.keepPolling && !options.keepPolling(data.value)) return
    timer = window.setTimeout(refresh, options.interval)
  }

  async function refresh() {
    loading.value = true
    try {
      data.value = await loader()
      error.value = null
    } catch (problem) {
      error.value = problem instanceof Error ? problem.message : String(problem)
    } finally {
      loading.value = false
      schedule()
    }
  }

  onMounted(refresh)
  onBeforeUnmount(() => {
    stopped = true
    window.clearTimeout(timer)
  })

  return { data, error, loading, refresh }
}

<template>
  <div class="bg-slate-50 text-slate-900">
    <section class="bg-white border-b border-slate-200">
      <div class="max-w-6xl mx-auto px-6 py-16 md:py-20">
        <p class="text-sm font-semibold text-primary-700 mb-4">
          {{ page.eyebrow }}
        </p>
        <h1 class="text-4xl md:text-5xl font-bold tracking-tight mb-6">
          {{ page.title }}
        </h1>
        <p class="text-lg md:text-xl text-slate-600 max-w-3xl leading-relaxed">
          {{ page.subtitle }}
        </p>
        <p class="text-base text-slate-500 max-w-3xl leading-relaxed mt-4">
          {{ page.intro }}
        </p>
        <div v-if="page.ctas?.length" class="flex flex-wrap gap-3 mt-8">
          <router-link
            v-for="cta in page.ctas"
            :key="cta.to"
            :to="cta.to"
            class="inline-flex items-center gap-2 rounded-lg bg-primary-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-800 transition"
          >
            <AppIcon :name="cta.icon || 'arrow-right'" :size="16" />
            {{ cta.label }}
          </router-link>
        </div>
      </div>
    </section>

    <section class="max-w-6xl mx-auto px-6 py-12 md:py-16 space-y-12">
      <article
        v-for="section in page.sections"
        :key="section.title"
        class="border-t border-slate-200 pt-8"
      >
        <h2 class="text-2xl font-bold text-slate-900 mb-4">
          {{ section.title }}
        </h2>
        <p v-if="section.body" class="text-slate-600 leading-relaxed mb-6">
          {{ section.body }}
        </p>

        <ol v-if="section.steps?.length" class="grid gap-3">
          <li
            v-for="(step, index) in section.steps"
            :key="step"
            class="flex gap-3 text-slate-700"
          >
            <span class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-50 text-sm font-bold text-primary-700">
              {{ index + 1 }}
            </span>
            <span class="leading-relaxed">{{ step }}</span>
          </li>
        </ol>

        <div v-if="section.cards?.length" class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="card in section.cards"
            :key="card.title"
            class="rounded-lg border border-slate-200 p-4 bg-slate-50"
          >
            <div class="flex items-center gap-2 mb-2">
              <AppIcon :name="card.icon || 'info'" :size="18" class="text-primary-700" />
              <h3 class="font-semibold text-slate-900">
                {{ card.title }}
              </h3>
            </div>
            <p class="text-sm text-slate-600 leading-relaxed">
              {{ card.text }}
            </p>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../../../icons/AppIcon.vue'
import { KORRIGO_PUBLIC_PAGES } from '../content/korrigoPublicContent'

const props = defineProps({
  pageKey: {
    type: String,
    required: true,
  },
})

const page = computed(() => KORRIGO_PUBLIC_PAGES[props.pageKey] || KORRIGO_PUBLIC_PAGES.home)
</script>

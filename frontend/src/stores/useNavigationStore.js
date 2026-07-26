import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNavigationStore = defineStore('navigation', () => {
  /** L1 active item: 'chat' | 'kb' | 'team' | 'settings' */
  const activeNav = ref('chat')

  /** Whether the L2 panel is expanded */
  const l2Expanded = ref(true)

  /** L2 panel width in px (resizable) */
  const l2Width = ref(280)

  /** Mobile sidebar Sheet open state */
  const mobileSidebarOpen = ref(false)

  /** Active settings section for settings page navigation */
  const activeSettingsSection = ref('overview')

  /** Active full-page view within a nav section */
  const activePage = ref('')

  /** Minimum and maximum L2 width */
  const L2_MIN = 240
  const L2_MAX = 440

  function setActiveNav(nav) {
    if (activeNav.value === nav) {
      // Clicking the same nav item toggles L2
      l2Expanded.value = !l2Expanded.value
    } else {
      activeNav.value = nav
      activePage.value = ''
      l2Expanded.value = true
    }
  }

  function toggleL2() {
    l2Expanded.value = !l2Expanded.value
  }

  function collapseL2() {
    l2Expanded.value = false
  }

  function expandL2() {
    l2Expanded.value = true
  }

  function setL2Width(width) {
    l2Width.value = Math.min(L2_MAX, Math.max(L2_MIN, width))
  }

  function toggleMobileSidebar() {
    mobileSidebarOpen.value = !mobileSidebarOpen.value
  }

  function openMobileSidebar() {
    mobileSidebarOpen.value = true
  }

  function closeMobileSidebar() {
    mobileSidebarOpen.value = false
  }

  function setActiveSettingsSection(section) {
    activeSettingsSection.value = section
  }

  function setActivePage(page) {
    activePage.value = page
  }

  return {
    activeNav,
    l2Expanded,
    l2Width,
    mobileSidebarOpen,
    activeSettingsSection,
    activePage,
    L2_MIN,
    L2_MAX,
    setActiveNav,
    toggleL2,
    collapseL2,
    expandL2,
    setL2Width,
    toggleMobileSidebar,
    openMobileSidebar,
    closeMobileSidebar,
    setActiveSettingsSection,
    setActivePage,
  }
})

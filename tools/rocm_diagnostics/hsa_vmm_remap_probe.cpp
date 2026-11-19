// HSA VMM alias and address reuse probe. Mismatch counts are bytes.
#include <hsa/hsa.h>
#include <hsa/hsa_ext_amd.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#define CHECK_HSA_STATUS(call) do { \
    hsa_status_t current_status_value = (call); \
    if (current_status_value != HSA_STATUS_SUCCESS) { \
        const char *current_message_value = nullptr; \
        hsa_status_string(current_status_value, &current_message_value); \
        std::fprintf(stderr, "HSA line=%d status=%u %s\n", __LINE__, \
                     unsigned(current_status_value), current_message_value ? current_message_value : ""); \
        return 2; \
    } \
} while (0)

struct GpuMemoryPoolSelection {
    hsa_agent_t gpu_agent_value{};
    hsa_amd_memory_pool_t gpu_pool_value{};
};

static hsa_status_t select_gpu_memory_pool(hsa_amd_memory_pool_t pool_value, void *context_value) {
    auto *selection_value = static_cast<GpuMemoryPoolSelection *>(context_value);
    hsa_amd_segment_t segment_value{};
    bool allocation_allowed_value = false;
    uint32_t global_flags_value = 0;
    if (hsa_amd_memory_pool_get_info(pool_value, HSA_AMD_MEMORY_POOL_INFO_SEGMENT, &segment_value) != HSA_STATUS_SUCCESS ||
        hsa_amd_memory_pool_get_info(pool_value, HSA_AMD_MEMORY_POOL_INFO_RUNTIME_ALLOC_ALLOWED, &allocation_allowed_value) != HSA_STATUS_SUCCESS ||
        segment_value != HSA_AMD_SEGMENT_GLOBAL || !allocation_allowed_value ||
        hsa_amd_memory_pool_get_info(pool_value, HSA_AMD_MEMORY_POOL_INFO_GLOBAL_FLAGS, &global_flags_value) != HSA_STATUS_SUCCESS ||
        (global_flags_value & HSA_AMD_MEMORY_POOL_GLOBAL_FLAG_FINE_GRAINED)) {
        return HSA_STATUS_SUCCESS;
    }
    selection_value->gpu_pool_value = pool_value;
    return HSA_STATUS_INFO_BREAK;
}

static hsa_status_t select_gpu_agent(hsa_agent_t agent_value, void *context_value) {
    hsa_device_type_t device_type_value{};
    if (hsa_agent_get_info(agent_value, HSA_AGENT_INFO_DEVICE, &device_type_value) != HSA_STATUS_SUCCESS ||
        device_type_value != HSA_DEVICE_TYPE_GPU) {
        return HSA_STATUS_SUCCESS;
    }
    auto *selection_value = static_cast<GpuMemoryPoolSelection *>(context_value);
    selection_value->gpu_agent_value = agent_value;
    hsa_status_t pool_status_value = hsa_amd_agent_iterate_memory_pools(agent_value, select_gpu_memory_pool, context_value);
    if (pool_status_value != HSA_STATUS_SUCCESS && pool_status_value != HSA_STATUS_INFO_BREAK) {
        return pool_status_value;
    }
    return selection_value->gpu_pool_value.handle ? HSA_STATUS_INFO_BREAK : HSA_STATUS_SUCCESS;
}

int main() {
    constexpr size_t allocation_size_bytes = 20 * 1024 * 1024;
    const char *address_mode_value = std::getenv("TRACE_ADDRESS_MODE");
    if (!address_mode_value || (std::strcmp(address_mode_value, "same") && std::strcmp(address_mode_value, "different"))) {
        std::fprintf(stderr, "TRACE_ADDRESS_MODE must be same or different\n");
        return 7;
    }
    CHECK_HSA_STATUS(hsa_init());
    GpuMemoryPoolSelection selection_value{};
    hsa_status_t selection_status_value = hsa_iterate_agents(select_gpu_agent, &selection_value);
    if ((selection_status_value != HSA_STATUS_SUCCESS && selection_status_value != HSA_STATUS_INFO_BREAK) ||
        !selection_value.gpu_pool_value.handle) {
        std::fprintf(stderr, "No usable GPU memory pool (status=%u)\n", unsigned(selection_status_value));
        return 4;
    }
    char gpu_agent_name_value[64]{};
    CHECK_HSA_STATUS(hsa_agent_get_info(selection_value.gpu_agent_value, HSA_AGENT_INFO_NAME, gpu_agent_name_value));
    std::fprintf(stderr, "HSA_GPU_AGENT=%s\n", gpu_agent_name_value);
    size_t allocation_granule_value = 0;
    CHECK_HSA_STATUS(hsa_amd_memory_pool_get_info(selection_value.gpu_pool_value, HSA_AMD_MEMORY_POOL_INFO_RUNTIME_ALLOC_GRANULE, &allocation_granule_value));
    if (!allocation_granule_value || allocation_size_bytes % allocation_granule_value) {
        std::fprintf(stderr, "Unsupported allocation granule: %zu\n", allocation_granule_value);
        return 6;
    }
    hsa_amd_memory_access_desc_t access_descriptor_value{HSA_ACCESS_PERMISSION_RW, selection_value.gpu_agent_value};
    std::vector<unsigned char> old_read_values(allocation_size_bytes), new_read_values(allocation_size_bytes);
    std::vector<unsigned char> old_fill_values(allocation_size_bytes, 0x17), new_fill_values(allocation_size_bytes, 0x3f);
    for (int iteration_index_value = 0; iteration_index_value < 20; ++iteration_index_value) {
        void *target_address_value = nullptr, *alias_address_value = nullptr, *spare_address_value = nullptr;
        hsa_amd_vmem_alloc_handle_t old_handle_value{}, new_handle_value{};
        CHECK_HSA_STATUS(hsa_amd_vmem_address_reserve(&target_address_value, allocation_size_bytes, 0, 0));
        CHECK_HSA_STATUS(hsa_amd_vmem_address_reserve(&alias_address_value, allocation_size_bytes, 0, 0));
        CHECK_HSA_STATUS(hsa_amd_vmem_handle_create(selection_value.gpu_pool_value, allocation_size_bytes, MEMORY_TYPE_NONE, 0, &old_handle_value));
        CHECK_HSA_STATUS(hsa_amd_vmem_map(target_address_value, allocation_size_bytes, 0, old_handle_value, 0));
        CHECK_HSA_STATUS(hsa_amd_vmem_set_access(target_address_value, allocation_size_bytes, &access_descriptor_value, 1));
        CHECK_HSA_STATUS(hsa_memory_copy(target_address_value, old_fill_values.data(), allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_amd_vmem_unmap(target_address_value, allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_amd_vmem_map(alias_address_value, allocation_size_bytes, 0, old_handle_value, 0));
        CHECK_HSA_STATUS(hsa_amd_vmem_set_access(alias_address_value, allocation_size_bytes, &access_descriptor_value, 1));
        CHECK_HSA_STATUS(hsa_amd_vmem_address_reserve(&spare_address_value, allocation_size_bytes, 0, 0));
        void *destination_address_value = std::strcmp(address_mode_value, "different") ? target_address_value : spare_address_value;
        CHECK_HSA_STATUS(hsa_amd_vmem_handle_create(selection_value.gpu_pool_value, allocation_size_bytes, MEMORY_TYPE_NONE, 0, &new_handle_value));
        CHECK_HSA_STATUS(hsa_amd_vmem_map(destination_address_value, allocation_size_bytes, 0, new_handle_value, 0));
        CHECK_HSA_STATUS(hsa_amd_vmem_set_access(destination_address_value, allocation_size_bytes, &access_descriptor_value, 1));
        CHECK_HSA_STATUS(hsa_memory_copy(destination_address_value, new_fill_values.data(), allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_memory_copy(old_read_values.data(), alias_address_value, allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_memory_copy(new_read_values.data(), destination_address_value, allocation_size_bytes));
        size_t old_mismatch_count = 0, new_mismatch_count = 0;
        for (size_t byte_index_value = 0; byte_index_value < allocation_size_bytes; ++byte_index_value) {
            old_mismatch_count += old_read_values[byte_index_value] != 0x17;
            new_mismatch_count += new_read_values[byte_index_value] != 0x3f;
        }
        std::printf("%d %zu %zu old=%02x new=%02x\n", iteration_index_value, old_mismatch_count, new_mismatch_count,
                    old_read_values[0], new_read_values[0]);
        std::fflush(stdout);
        CHECK_HSA_STATUS(hsa_amd_vmem_unmap(alias_address_value, allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_amd_vmem_unmap(destination_address_value, allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_amd_vmem_address_free(spare_address_value, allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_amd_vmem_handle_release(old_handle_value));
        CHECK_HSA_STATUS(hsa_amd_vmem_handle_release(new_handle_value));
        CHECK_HSA_STATUS(hsa_amd_vmem_address_free(alias_address_value, allocation_size_bytes));
        CHECK_HSA_STATUS(hsa_amd_vmem_address_free(target_address_value, allocation_size_bytes));
    }
    CHECK_HSA_STATUS(hsa_shut_down());
    return 0;
}

document.addEventListener('DOMContentLoaded', function() {
    let filterCount = 1;

    function updateFilterCount() {
        document.getElementById("filter_count").value = filterCount;
    }

    function createFilter() {
        const newFilter = document.createElement("div");
        newFilter.classList.add("custom-dropdown");

        newFilter.innerHTML = `
            <label id="filter-label" for="filter_${filterCount}">Hvem skal også være på billederne:</label>
            <select name="filter_${filterCount}" id="filter_${filterCount}">
                ${people.map(person => `<option value="${person}">${person}</option>`).join('')}
            </select>
        `;

        document.getElementById("additional-filters").appendChild(newFilter);
        filterCount++;
        updateFilterCount();
    }

    function removeFilter() {
        const additionalFilters = document.getElementById("additional-filters");
        const lastFilter = additionalFilters.lastElementChild;

        if (lastFilter) {
            additionalFilters.removeChild(lastFilter);
            filterCount--;
            updateFilterCount();
        }
    }

    document.getElementById("add-filter").addEventListener("click", createFilter);
    document.getElementById("remove-filter").addEventListener("click", removeFilter);
});

namespace Shop.Api.IntegrationTests;

public sealed class OrderStateEndpointTests(ApiFixture fixture)
{
    [Fact]
    public async Task SetOrderState_ForAnAllowedMove_Returns204AndWritesTheState()
    {
        await fixture.InsertOrderAsync("A-500", OrderState.Paid);

        var response = await fixture.Client.PutAsJsonAsync(
            "/api/v1/orders/A-500/state", new { state = "Packed", note = "boxed" });

        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);
        Assert.Equal(OrderState.Packed, (await fixture.ReadOrderAsync("A-500")).State);
    }

    [Fact]
    public async Task SetOrderState_WithAStateOutsideTheSettableSet_Returns400()
    {
        await fixture.InsertOrderAsync("A-501", OrderState.Paid);

        var response = await fixture.Client.PutAsJsonAsync(
            "/api/v1/orders/A-501/state", new { state = "Cancelled" });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(OrderState.Paid, (await fixture.ReadOrderAsync("A-501")).State);
    }
}

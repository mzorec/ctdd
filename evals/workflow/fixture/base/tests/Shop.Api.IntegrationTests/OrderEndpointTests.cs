namespace Shop.Api.IntegrationTests;

public sealed class OrderEndpointTests(ApiFixture fixture)
{
    [Fact]
    public async Task GetOrder_ForAnUnknownNumber_Returns404()
    {
        var response = await fixture.Client.GetAsync("/api/v1/orders/NOPE-1");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }
}

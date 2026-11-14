namespace Shop.Persistence.IntegrationTests;

public sealed class OrderRepositoryTests(DatabaseFixture fixture)
{
    [Fact]
    public async Task Get_ReturnsTheOrder_ForAKnownNumber()
    {
        await fixture.InsertOrderAsync("A-100", OrderState.Paid);

        var order = await fixture.Orders.GetAsync("A-100", CancellationToken.None);

        Assert.Equal(OrderState.Paid, order!.State);
    }
}
